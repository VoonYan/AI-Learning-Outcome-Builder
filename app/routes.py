from flask import render_template, redirect, url_for, flash, request, session, Blueprint, jsonify, current_app, abort
from flask_login import current_user, login_required
from .forms import NewUnitForm, AdminForm, EditUnitForm
from . import db
from .models import db, Unit, LearningOutcome, UserType
from . import create_app, config_manager
from sqlalchemy import case, update
import csv
import pandas as pd
from io import TextIOWrapper
from sqlalchemy.exc import IntegrityError
from .ai_evaluate import run_eval
import os
import json
import random

main = Blueprint('main', __name__)


@main.route('/home')
@main.route('/home_page')
def home(): 
    return render_template('homepage_purebs.html' )


@main.route('/dashboard')
@main.route('/main_page')
@main.route('/')
@login_required
def main_page(): 
    return render_template('main_page.html', title=f'{current_user.username} Dashboard', username=current_user.username)


@main.route('/create_lo/<int:unit_id>')
@login_required
def create_lo(unit_id):
    if current_user.role not in [UserType.ADMIN, UserType.UC]:
        abort(401)
    unit_id = request.args.get("unit_id", type=int)
    unit = Unit.query.get(unit_id) if unit_id else Unit.query.first()
    outcomes = unit.learning_outcomes if unit else []
    headings = ['#', 'Learning Outcome', 'Assessment', 'Delete', 'Reorder']
    return render_template('create_lo.html', title=f'Creation Page', username=current_user.username, unit=unit, outcomes=outcomes, headings=headings)

#all of this should be moved to some new api file

@main.delete("/lo_api/delete/<int:unit_id>/<int:lo_id>")
@login_required
def lo_delete(unit_id, lo_id):
    lo = LearningOutcome.query.get_or_404(lo_id)
    db.session.delete(lo)
    db.session.commit()
    flash("Outcome deleted", "success")
    return jsonify({"ok": True})


def returnLOOpener(level):
    currentConfig = config_manager.getCurrentParams()
    LEVEL_NAME = {
        1: currentConfig["Level 1"],
        2: currentConfig["Level 2"],
        3: currentConfig["Level 3"],
        4: currentConfig["Level 4"],
        5: currentConfig["Level 5"],
        6: currentConfig["Level 6"]
    }
    loLevel = LEVEL_NAME[level].upper()
    wordlist = currentConfig[loLevel]
    keyWord = random.choice(wordlist)
    keyWord += '... '
    return keyWord


@main.post("/lo_api/add/<int:unit_id>")
@login_required
def lo_add(unit_id):
    unit = Unit.query.filter_by(id=unit_id).first()
    existing_los = LearningOutcome.query.filter_by(unit_id=unit_id).all()
    blank_lo = LearningOutcome(unit_id=unit_id, position=len(existing_los)+1, description=returnLOOpener(unit.level))
    db.session.add(blank_lo)
    db.session.commit()
    flash("Outcome Added and Saved", "success")
    return jsonify({"ok": True})

@main.post("/lo_api/reorder/<int:unit_id>")
@login_required
def lo_reorder(unit_id):
    data = request.get_json(force=True)
    order = data.get("order", [])
    unit_id = data.get("unit_id")
    if not order:
        return jsonify({"ok": False, "error": "empty order"}), 400
    if unit_id is not None:
        count = LearningOutcome.query.filter(
            LearningOutcome.id.in_(order),
            LearningOutcome.unit_id == unit_id
        ).count()
        if count != len(order):
            return jsonify({"ok": False, "error": "ids mismatch for unit"}), 400
    order = [int(x) for x in order]
    order_map = {lo_id: pos for pos, lo_id in enumerate(order, start=1)}
    stmt = (
        update(LearningOutcome)
        .where(LearningOutcome.id.in_(order))
        .values(position=case(order_map, value=LearningOutcome.id))
    )
    db.session.execute(stmt)
    db.session.commit()
    return jsonify({"ok": True})


@main.post("/lo_api/save/<int:unit_id>")
@login_required
def lo_save(unit_id):
    loList = LearningOutcome.query.filter_by(unit_id=unit_id).all()
    newLoDict = json.loads(request.data)
    # assume the order we recieve them is the order they are intended to be in
    for lo, newLOData in zip(loList, newLoDict.values()):
        lo.description = newLOData[0]
        lo.assessment = newLOData[1]
        db.session.add(lo)
    db.session.commit()
    return jsonify({'status': 'ok'})


#we need a button to export all of the units, and im assuming this is for one specific unit, perhaps a general function with single unit option is best here 
@main.get("/lo_api/export.csv/<int:unit_id>")
@login_required
def lo_export_csv(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    rows = unit.learning_outcomes
    import csv, io
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["#", "Description", "Assessment", "Position"])
    for i, lo in enumerate(rows, start=1):
        writer.writerow([i, lo.description, lo.assessment or "", lo.position])
    out = buf.getvalue()
    return (out, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": f'attachment; filename="{unit.unitcode}_outcomes.csv"'
    })


@main.post("/lo_api/evaluate/<int:unit_id>")
@login_required
def ai_evaluate(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    rows = unit.learning_outcomes
    outcomes_text = "\n".join(lo.description for lo in rows)
    try:
        result = run_eval(
            unit.level, unit.unitname, unit.creditpoints, outcomes_text
        )

        return jsonify({"ok": True, "html": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@main.route('/search_unit', methods=['GET', 'POST'])
def search_unit():
    if request.method == "GET":

        #normal search
        query = request.args.get("query", "").strip()
        filter_type = request.args.get("filter", "name")
        sort_by = request.args.get("sort", "unitcode")  # default sorting

        results = []

        if query:
            if filter_type == "code":
                results = Unit.query.filter(Unit.unitcode.ilike(f"%{query}%")).all()
            else:
                results = Unit.query.filter(Unit.unitname.ilike(f"%{query}%")).all()
        else:
            # Empty query → fetch all units
            results = Unit.query.all()

            # Sorting
            if sort_by == "unitcode":
                results.sort(key=lambda u: u.unitcode)
            elif sort_by == "unitlevel":
                results.sort(key=lambda u: u.level)

        return render_template(
            'search_unit.html',
            title='Unit Search',
            username=current_user.username if not current_user.is_anonymous else 'Guest',
            results=results,
            query=query,
            filter_type=filter_type,
            sort_by=sort_by
        )


@main.route('/view/<int:unit_id>', methods=['GET'])
def view(unit_id):
    if request.method == "GET":
        unit = Unit.query.filter_by(id=unit_id).first()
        if not unit:
            abort(404)
        print(unit.unitname)
        return render_template("view.html", title="Unit Details", unit=unit, UserType=UserType)

@main.route('/unit/<int:unit_id>/edit_unit', methods=['GET', 'POST'])
@login_required
def edit_unit(unit_id):
    unit = Unit.query.filter_by(id=unit_id).first_or_404()
    form = EditUnitForm()
    if current_user.userType != UserType.ADMIN and unit.creatorid != current_user.id:
        abort(401)
    if request.method == "GET":
        form.unitcode.data = unit.unitcode
        form.unitname.data = unit.unitname
        form.level.data = unit.level
        form.creditpoints.data = unit.creditpoints
        form.description.data = unit.description
        return render_template("edit_unit.html", unit=unit, form=form)

    if request.method == "POST":
        data = request.form

        # check unique constraint first
        unitcodeCheck = Unit.query.filter_by(unitcode=data["unitcode"].strip().upper()).first()
        if unitcodeCheck != None and unitcodeCheck.id != unit.id:
            flash("That unit code already exists. Please choose a different one.", "danger")
            # re-render the form with user’s input
            # that would be difficult with this implementation and not a priority at the moment.
            return render_template("edit_unit.html", unit=unit, form=form)

        # update fields
        unit.unitcode = data["unitcode"].strip().upper()   # normalize to uppercase if needed
        unit.unitname = data["unitname"].strip()
        unit.level = int(data["level"])
        unit.creditpoints = int(data["creditpoints"])
        unit.description = data["description"].strip()

        db.session.commit()
        flash("Unit updated successfully!", "success")
        # redirect using the (possibly new) unitcode
        return redirect(url_for("main.view", unit_id=unit.id))

@main.route('/new_unit', methods = ['GET', 'POST'])
@login_required
def new_unit():
    if current_user.role not in [UserType.ADMIN, UserType.UC]:
        abort(401)

    form = NewUnitForm()
    if request.method == 'GET':
        return render_template('new_unit_form.html', title=f'Create New Unit', username=current_user.username, form=form)
    
    if request.method == 'POST':
        if not form.validate():
            return render_template('new_unit_form.html', title=f'Create New Unit', username=current_user.username, form=form)
        data = request.form
        newUnit = Unit(
            unitcode=data["unitcode"], 
            unitname=data["unitname"], 
            level=data["level"], 
            creditpoints=data["creditpoints"], 
            description=data["description"],
            creatorid = current_user.id
            )
        db.session.add(newUnit)
        db.session.commit()
        flash("Unit Created", 'success')
        return redirect("/main_page")
    

@main.route('/delete_unit/<int:unit_id>', methods = ['DELETE'])
@login_required
def delete_unit(unit_id):
    unit = Unit.query.filter_by(id=unit_id).first_or_404()
    if current_user.userType != UserType.ADMIN and unit.creatorid != current_user.id:
        abort(401)

    if request.method == 'DELETE':
        db.session.delete(unit)
        db.session.commit()
        flash("Unit Deleted", 'success')
        return jsonify({"ok": True})


#small helper functions
def listToStringByComma(List):
    return ', '.join(List)

def intListToStringByDash(List):
    return '-'.join(str(x) for x in List)

def intStringToListByDash(String):
    return list(map(int, String.split('-')))

#update function, bit ugly might move it 
def updateAIParams(data):
    config_manager.replaceCurrentParameter("selected_model", data["model"])
    config_manager.replaceCurrentParameter("API_key", data["apikey"])
    config_manager.replaceCurrentParameter("KNOWLEDGE", data["knowledge"].split(', '))
    config_manager.replaceCurrentParameter("COMPREHENSION", data["comprehension"].split(', '))
    config_manager.replaceCurrentParameter("APPLICATION", data["application"].split(', '))
    config_manager.replaceCurrentParameter("ANALYSIS", data["analysis"].split(', '))
    config_manager.replaceCurrentParameter("SYNTHESIS", data["synthesis"].split(', '))
    config_manager.replaceCurrentParameter("EVALUATION", data["evaluation"].split(', '))
    config_manager.replaceCurrentParameter("BANNED", data["banned"].split(', '))
    config_manager.replaceCurrentParameter("Level 1", data["level1"])
    config_manager.replaceCurrentParameter("Level 2", data["level2"])
    config_manager.replaceCurrentParameter("Level 3", data["level3"])
    config_manager.replaceCurrentParameter("Level 4", data["level4"])
    config_manager.replaceCurrentParameter("Level 5", data["level5"])
    config_manager.replaceCurrentParameter("Level 6", data["level6"])
    config_manager.replaceCurrentParameter("6 Points", intStringToListByDash(data["cp6"]))
    config_manager.replaceCurrentParameter("12 Points", intStringToListByDash(data["cp12"]))
    config_manager.replaceCurrentParameter("24 Points", intStringToListByDash(data["cp24"]))

@main.route('/admin', methods = ['GET', 'POST'])
@login_required
def admin():
    if current_user.userType != UserType.ADMIN:
        flash("You do not have permission to access that page.", "danger")
        return redirect(url_for("main.home")) 
    form = AdminForm()
    if request.method == 'GET':
        #this creates the config for jinja based on the config since config needs lists but jinja needs strings, this could be done in jina with many more lines 
        loadconfig = config_manager.getCurrentParams()
        loadconfig["6 Points"] = intListToStringByDash(loadconfig["6 Points"])
        loadconfig["12 Points"] = intListToStringByDash(loadconfig["12 Points"])
        loadconfig["24 Points"] = intListToStringByDash(loadconfig["24 Points"])
        form.knowledge.data = listToStringByComma(loadconfig['KNOWLEDGE'])
        form.comprehension.data = listToStringByComma(loadconfig['COMPREHENSION'])
        form.application.data = listToStringByComma(loadconfig['APPLICATION'])
        form.analysis.data = listToStringByComma(loadconfig['ANALYSIS'])
        form.synthesis.data = listToStringByComma(loadconfig['SYNTHESIS'])
        form.evaluation.data = listToStringByComma(loadconfig['EVALUATION'])
        form.banned.data = listToStringByComma(loadconfig['BANNED'])
        return render_template('admin_page_template.html', form=form, config=loadconfig, getattr=getattr)

    if request.method == 'POST':
        if not form.validate():
            flash("Failed To Validate Form.", 'error')
            return redirect('admin')
        updateAIParams(request.form)
        flash("Settings Successfully Updated.", 'success')
        return redirect('admin')
    
#this is the reset to default, it is only accessable by post requests from admin users
@main.route('/AI_reset', methods = ['POST'])
@login_required
def AI_reset():
    if current_user.userType != UserType.ADMIN:
        return "Unauthorised", 401
    if request.method == 'POST':
        if request.data == b'Reset': #this if is useless but might be expandable for security
            config_manager.resetParamsToDefault()
            flash("Settings Successfully Reset to Default.", 'success')
            return jsonify({'status': 'ok'})
        return "Failed To Reset To Default", 500


@main.route('/bloom-guide')
def bloom_guide():
    """
    Display the Bloom's Taxonomy guide page with current configuration
    """
    # Get current AI configuration parameters
    config = config_manager.getCurrentParams()

    # Process the credit points data to make it template-friendly
    config['6_Points_Min'] = config['6 Points'][0]
    config['6_Points_Max'] = config['6 Points'][1]
    config['12_Points_Min'] = config['12 Points'][0]
    config['12_Points_Max'] = config['12 Points'][1]
    config['24_Points_Min'] = config['24 Points'][0]
    config['24_Points_Max'] = config['24 Points'][1]

    # Convert lists to JSON strings for JavaScript
    config_json = {
        'KNOWLEDGE': config['KNOWLEDGE'],
        'COMPREHENSION': config['COMPREHENSION'],
        'APPLICATION': config['APPLICATION'],
        'ANALYSIS': config['ANALYSIS'],
        'SYNTHESIS': config['SYNTHESIS'],
        'EVALUATION': config['EVALUATION'],
        'BANNED': config['BANNED'],
        'Level 1': config['Level 1'],
        'Level 2': config['Level 2'],
        'Level 3': config['Level 3'],
        'Level 4': config['Level 4'],
        'Level 5': config['Level 5'],
        'Level 6': config['Level 6'],
        '6 Points': config['6 Points'],
        '12 Points': config['12 Points'],
        '24 Points': config['24 Points']
    }

    return render_template('bloom_guide.html', config=config, config_json=json.dumps(config_json))
