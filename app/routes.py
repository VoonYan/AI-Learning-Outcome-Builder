from flask import render_template, redirect, url_for, flash, request, session, Blueprint, jsonify, abort
from flask_login import current_user, login_required
from .forms import NewUnitForm, AdminForm, EditUnitForm
from . import db
from .models import db, Unit, LearningOutcome, UserType
from . import create_app, config_manager
from sqlalchemy import case, update
import csv
import pandas as pd
import io
from sqlalchemy.exc import IntegrityError


main = Blueprint('main', __name__)



@main.route('/main_page')
@main.route('/')
def home(): 
    return render_template('homepage_purebs.html' )

@main.route('/main-page')
@login_required
def main_page(): 
    return render_template('main_page.html', title=f'{current_user.username} Dashboard', username=current_user.username)


@main.route('/create-lo')
@login_required
def create_lo():
    unit_id = request.args.get("unit_id", type=int)
    unit = Unit.query.get(unit_id) if unit_id else Unit.query.first()
    outcomes = unit.learning_outcomes if unit else []
    headings = ['#', 'Learning Outcome', 'Assessment', 'Delete', 'Reorder']
    return render_template('create_lo.html', title=f'Creation Page', username=current_user.username, unit=unit, outcomes=outcomes, headings=headings)


@main.post("/lo/<int:lo_id>/delete")
def lo_delete(lo_id):
    lo = LearningOutcome.query.get_or_404(lo_id)
    unit_id = lo.unit_id
    db.session.delete(lo)
    db.session.commit()
    flash("Outcome deleted", "success")
    return redirect(url_for("main.create_lo", unit_id=unit_id))


@main.post("/lo/reorder")
def lo_reorder():
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


@main.post("/lo/save")
def lo_save():
    unit_id = request.form.get("unit_id", type=int)
    flash("Outcomes saved.", "success")
    return redirect(url_for("main.create_lo", unit_id=unit_id))


@main.get("/lo/export.csv")
def lo_export_csv():
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


@main.post("/lo/evaluate")
def ai_evaluate():
    unit_id = request.args.get("unit_id", type=int)
    unit = Unit.query.get(unit_id) if unit_id else Unit.query.first()
    rows = unit.learning_outcomes if unit else []
    # For now, just echo simple HTML; later hook up the real AI
    items = "".join(f"<li>{lo.description} — {lo.assessment or ''}</li>" for lo in rows)
    return f"<ul class='mb-0'>{items or '<li>No outcomes</li>'}</ul>"


@main.route('/search_unit', methods=['GET', 'POST'])
@login_required
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
            username=current_user.username,
            results=results,
            query=query,
            filter_type=filter_type,
            sort_by=sort_by
        )


@main.route('/view/<int:unit_id>', methods=['GET'])
@login_required
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
    if current_user.userType != UserType.ADMIN or unit.creatorid != current_user.id:
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
    form = NewUnitForm()
    if request.method == 'GET':
        return render_template('new_unit_form.html', title=f'Create New Unit', username=current_user.username, form=form)
    
    if request.method == 'POST':
        if not form.validate():
            return render_template('new_unit_form.html', title=f'Create New Unit', username=current_user.username, form=form)
        data = request.form
        unitcodeCheck = db.session.query(Unit).filter_by(unitcode=data["unitcode"]).first()
        if unitcodeCheck != None:
            flash("Unit already Exists", 'error')
            return redirect("/new_unit")
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
    

# Expected Formatting for import export
# this should realistically be handled by the config manager, or something like it but its not completable at the moment
expectedIOFormatting = {
    #implemented
    'code' :        'code',
    'title':        'title',
    'level':        'level',
    'Outcomes':     'Outcomes',

    #not included in the dataset at the moment
    'CreditPoints': 'CreditPoints', 

    #unimplemented
    'Assessments':  'Assessments',
    'Faculty':      'Faculty',
    'ROE':          'ROE',
    'UnitType':     'UnitType',
    'Curriculum':   'Curriculum',
    'Content':      'Content',

    #delimiters 
    'loDelimiter' : '|*|',
    'loAssessmentDelimiter': '|',
}

@main.route('/import-units', methods=['POST'])
@login_required
def import_units():
    # open file
    file = request.files.get("import_file")
    if not file:
        flash("No file uploaded", "danger")
        return redirect(url_for("main.main_page"))

    # check file extension
    if file.filename.endswith('xlsx') or file.filename.endswith('xls'):
        df = pd.read_excel(file)
        pass
    elif file.filename.endswith('csv'):
        df = pd.read_csv(file)
        pass
    else:
        flash('File type not supported', 'error')
        return redirect(url_for("main.main_page"))
    # process data
    unitcount =0
    hasDuplicates = False
    dupCount = 0
    hasLacksUnitCode = False
    codeCount = 0
    for _, newUnit in df.iterrows():
        # checks
        if pd.isna(newUnit[expectedIOFormatting['code']]):
            hasLacksUnitCode = True
            codeCount += 1
            continue
        # db.session shouldnt be typically used but here we are checking our local session so its needed
        unitcodeCheck = db.session.query(Unit).filter_by(unitcode=str(newUnit[expectedIOFormatting['code']]).strip()).first()
        if unitcodeCheck != None:
            hasDuplicates = True
            dupCount += 1
            continue

        #create unit
        dbUnit = Unit(
            unitcode= str(newUnit[expectedIOFormatting['code']]).strip(), 
            unitname= newUnit[expectedIOFormatting['title']], 
            level= newUnit[expectedIOFormatting['level']], 
            #creditpoints is not provided by the dataset
            #creditpoints = 
            description= newUnit[expectedIOFormatting['Content']],
            creatorid = current_user.id
            )
        db.session.add(dbUnit)
        db.session.flush()
        unitcount+=1
        
        loPos = 1
        for lo in str(newUnit.Outcomes).split(expectedIOFormatting['loDelimiter']):
            lo = lo.split(expectedIOFormatting['loAssessmentDelimiter'])[0]

            if lo == '':
                continue

            dbLO = LearningOutcome(
                unit_id= dbUnit.id, 
                position= loPos, 
                description= lo
            )
            db.session.add(dbLO)
            loPos+=1
    db.session.commit()

    msg = f"{unitcount} units added successfully from file. "
    if hasLacksUnitCode:
        msg += f"{codeCount} units lacked a unitcode and were skipped. "
    if hasDuplicates:
        msg += f"{dupCount} units were duplicates and were skipped. "
    print(unitcount)
    flash(msg, "success")
    return redirect(url_for("main.main_page"))

def createCSVofLOs(userID=-1):
    if userID != -1:
        units = Unit.query.filter_by(creatorid=current_user.id).all()
    else:
        units = Unit.query.all()
    
    df = pd.DataFrame(
        columns=[
            expectedIOFormatting["code"], 
            expectedIOFormatting["title"], 
            expectedIOFormatting["level"], 
            expectedIOFormatting["CreditPoints"], 
            expectedIOFormatting["Content"],
            expectedIOFormatting["Outcomes"]
        ])
    
    for unit in units:
        loString = ''
        for lo in unit.learning_outcomes:
            loString += lo.description + expectedIOFormatting["loAssessmentDelimiter"] + expectedIOFormatting["loDelimiter"]
        #create df row by row
        df.loc[unit.id] = [
            unit.unitcode,
            unit.unitname,
            unit.level,
            unit.creditpoints,
            unit.description,
            loString
        ]
    buf = io.StringIO()
    df.to_csv(buf)
    return buf.getvalue()


@main.route('/export_my_units')
@login_required
def export_my_units():
    out = createCSVofLOs(current_user.id)
    return (out, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="units_and_outcomes.csv"'
    })


@main.route('/export_all_units')
@login_required
def export_all_units():
    out = createCSVofLOs()
    return (out, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="units_and_outcomes.csv"'
    })