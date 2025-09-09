from flask import render_template, redirect, url_for, flash, request, session, Blueprint, jsonify
from flask_login import current_user, login_required
from .forms import NewUnitForm, AdminForm
from . import db
from .models import db, Unit, LearningOutcome, UserType
from . import create_app, config_manager
from sqlalchemy import case, update
import csv
import pandas as pd
from io import TextIOWrapper


main = Blueprint('main', __name__)


@main.route('/main-page')
@main.route('/')
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
    if request.method == "POST":
        file = request.files.get("upload_file")
        if not file:
            flash("No file uploaded", "danger")
            return redirect(url_for("main.search_unit"))

        filename = file.filename.lower()
        defaults_applied = False
        duplicates = []

        def safe_int(value, default):
            try:
                return int(value)
            except (ValueError, TypeError):
                defaults_applied = True
                return default

        try:
            rows = []

            # --- Read file ---
            if filename.endswith(".csv"):
                stream = TextIOWrapper(file.stream, encoding="utf-8")
                reader = csv.reader(stream)
                rows = list(reader)
            elif filename.endswith(".xlsx"):
                df = pd.read_excel(file, header=None, engine="openpyxl")
                rows = df.values.tolist()
            else:
                flash("Unsupported file format. Upload CSV or Excel.", "danger")
                return redirect(url_for("main.search_unit"))

            # --- Detect headers ---
            first_row = rows[0]
            header_keywords = ["unitcode", "unitname", "level", "creditpoints", "description"]
            if any(str(cell).lower() in header_keywords for cell in first_row):
                # File has headers
                if filename.endswith(".csv"):
                    stream.seek(0)
                    reader = csv.DictReader(stream)
                    rows = list(reader)
                else:
                    df = pd.read_excel(file, engine="openpyxl")
                    rows = df.to_dict(orient="records")
            else:
                # No headers → smart parser
                formatted_rows = []
                for row in rows:
                    row = [str(cell).strip() if cell not in [None, ""] else None for cell in row]
                    unitcode = unitname = level = creditpoints = description = None

                    if len(row) >= 5:
                        unitcode, unitname, level, creditpoints, description = row[:5]
                    elif len(row) == 4:
                        unitcode, unitname, level, creditpoints = row
                    elif len(row) == 3:
                        unitcode, unitname, level = row
                    elif len(row) == 2:
                        unitcode, unitname = row
                    elif len(row) == 1:
                        unitcode = row[0]

                    # Smart auto-detection: if unitname is numeric
                    if unitname and str(unitname).isdigit():
                        description = creditpoints
                        creditpoints = level
                        level = unitname
                        unitname = None

                    formatted_rows.append({
                        "unitcode": unitcode,
                        "unitname": unitname,
                        "level": level,
                        "creditpoints": creditpoints,
                        "description": description
                    })
                rows = formatted_rows

            # --- Process rows ---
            for row in rows:
                unit_code = row.get("unitcode")
                unit_name = row.get("unitname")
                level = row.get("level")
                credit_points = row.get("creditpoints")
                description = row.get("description")

                # Apply defaults and safe conversions
                if not unit_name or (isinstance(unit_name, float) and pd.isna(unit_name)):
                    unit_name = "default name"
                    defaults_applied = True

                level = safe_int(level, 1)
                credit_points = safe_int(credit_points, 6)

                if not description or (isinstance(description, float) and pd.isna(description)):
                    # If description missing, try last column text
                    if isinstance(row.get("creditpoints"), str):
                        description = row.get("creditpoints")
                    else:
                        description = "no description"
                    defaults_applied = True

                if unit_code:
                    existing = Unit.query.filter_by(unitcode=unit_code).first()
                    if existing:
                        duplicates.append(unit_code)
                    else:
                        new_unit = Unit(
                            unitcode=unit_code,
                            unitname=str(unit_name),
                            level=int(level),
                            creditpoints=int(credit_points),
                            description=str(description)
                        )
                        db.session.add(new_unit)

            db.session.commit()

            # Flash success messages
            msg = "Units added successfully from file."
            if defaults_applied:
                msg += " Missing fields were filled with default values."
            flash(msg, "success")

            if duplicates:
                flash("The following units already exist and were skipped: " + ", ".join(duplicates), "warning")

        except Exception as e:
            flash(f"Error processing file: {str(e)}", "danger")

        return redirect(url_for("main.search_unit"))

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


@main.route('/view', methods=['GET', 'POST'])
@login_required
def view():
    unit_code = request.args.get("code")
    if not unit_code:
        abort(404)

    unit = Unit.query.filter_by(unitcode=unit_code).first()
    if not unit:
        abort(404)

    if request.method == "POST":
        #only if user is admin or unit creator
        if not (current_user.userType == UserType.ADMIN or current_user.id == unit.creator_id):
            abort(403)  # Forbidden
        # update unit from form data
        unit.unitname = request.form.get("unitname")
        unit.creditpoints = request.form.get("creditpoints")  # optional if editable
        unit.description = request.form.get("description")
        # add more fields as needed
        db.session.commit()
        flash("Unit updated successfully", "success")
        return redirect(url_for("main.view", code=unit.unitcode))

    return render_template("view.html", title="Unit Details", unit=unit)


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
    