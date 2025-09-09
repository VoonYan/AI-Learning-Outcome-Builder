from flask import render_template, redirect, url_for, flash, request, session, Blueprint, jsonify,current_app
from flask_login import current_user, login_required
from .forms import NewUnitForm, AdminForm
from . import db
from .models import db, Unit, LearningOutcome, UserType
from . import create_app, config_manager
from sqlalchemy import case, update
from .ai_evaluate import run_eval
import os
import json


main = Blueprint('main', __name__)


@main.route('/')
def homepage():
    return render_template('homepage.html' )

@main.route('/main-page')
@login_required
def main_page(): 
    return render_template('main_page.html', title=f'{current_user.username} Dashboard', username=current_user.username)

@main.route('/main-page2')
def main_page2(): 
    return render_template('main_page2.html' )

@main.route('/navbar')
def navbar():
    return render_template('admin_page.html')

@main.route('/base')
@login_required
def base_main(): 
    return render_template('base_main.html', title=f'{current_user.username} Dashboard', username=current_user.username)

@main.route('/create_lo/<int:unit_id>')
@login_required
def create_lo(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    outcomes = unit.learning_outcomes
    #why are we parsing headings here?
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

@main.post("/lo_api/add/<int:unit_id>")
@login_required
def lo_add(unit_id):
    existing_los = LearningOutcome.query.filter_by(unit_id=unit_id).all()
    blank_lo = LearningOutcome(unit_id=unit_id, position=len(existing_los)+1, description="")
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
    print(newLoDict)
    for lo in loList:
        newLOData = newLoDict[str(lo.position)]
        lo.description = newLOData[0]
        lo.assessment = newLOData[1]
        db.session.add(lo)
    
    db.session.commit()
    return jsonify({'status': 'ok'})


#we need a button to export all of the units, and im assuming this is for one specific unit, perhaps a general function with single unit option is best here 
@main.get("/lo_api/export.csv/<int:unit_id>")
def lo_export_csv(unit_id):
    unit_id = request.args.get("unit_id", type=int)
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


@main.route('/search_unit')
@login_required
def search_unit():
    return render_template('search_unit.html', title=f'Creation Page', username=current_user.username)

@main.route('/view')
@login_required
def view():
    return render_template('view.html', title="Unit Details")


@main.route('/new_unit', methods = ['GET', 'POST'])
@login_required
def new_unit():
    form = NewUnitForm()
    if request.method == 'GET':
        return render_template('new_unit_form.html', title=f'Create New Unit', username=current_user.username, form=form)
    
    if request.method == 'POST':
        if not form.validate():
            return render_template('new_unit_form.html', title=f'Create New Unit', username=current_user.username, form=form)
        data = request.form
        newUnit = Unit(unitcode=data["unitcode"], unitname=data["unitname"], level=data["level"], creditpoints=data["creditpoints"], description=data["description"])
        db.session.add(newUnit)
        db.session.commit()
        flash("Unit Created", 'success')
        return redirect("/main-page")

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
        return "Unauthorised", 401
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
        return render_template('admin_page_template.html', form=form, config=loadconfig)

    if request.method == 'POST':
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
    