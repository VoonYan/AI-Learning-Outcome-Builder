"""
Main routing module for the AI Learning Outcome Builder application.

This module contains all the Flask routes and view functions for the application,
including unit management, learning outcome operations, import/export functionality,
and admin controls. Routes are organized by functionality with appropriate
authentication and authorization checks.

Blueprint: 'main' - Contains all non-authentication routes
"""

from flask import render_template, redirect, url_for, flash, request, session, Blueprint, jsonify, current_app, abort
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
from .ai_evaluate import run_eval
import os
import json
import random

# Create main blueprint for all non-auth routes
main = Blueprint('main', __name__)


# ==================== NAVIGATION ROUTES ====================

@main.route('/')
def auto_route():
    """
    Root route handler with automatic redirection based on authentication status.

    Redirects anonymous users to the public homepage and authenticated users
    to their dashboard. This provides a seamless entry point for all user types.

    Returns:
        Redirect to appropriate page based on authentication status
    """
    if current_user.is_anonymous:
        return redirect(url_for('main.home'))
    else:
        return redirect(url_for('main.main_page'))


@main.route('/home')
@main.route('/home_page')
def home():
    """
    Public homepage route accessible to all users.

    Displays the landing page with information about the system and
    access options for different user types (Guest, Unit Coordinator, Admin).

    Returns:
        Rendered homepage template
    """
    return render_template('homepage.html')


@main.route('/dashboard')
@main.route('/main_page')
@login_required
def main_page():
    """
    Authenticated user dashboard.

    Main hub for logged-in users providing access to all features based on
    user role. Displays personalized greeting and navigation options.

    Returns:
        Rendered dashboard template with user context
    """
    return render_template(
        'main_page.html',
        title=f'{current_user.username} Dashboard',
        username=current_user.username
    )


# ==================== HELPER FUNCTIONS ====================

def getBloomsWordList(unitLevel):
    """
    Get Bloom's Taxonomy action words for a specific unit level.

    Retrieves the appropriate action verbs from configuration based on
    the unit's academic level, used for suggesting learning outcome starters.

    Args:
        unitLevel (int): Academic level of the unit (1-6)

    Returns:
        list: Action verbs appropriate for the unit level
    """
    currentConfig = config_manager.getCurrentParams()
    bloomLevel = currentConfig[f'Level {unitLevel}']
    levelTerms = bloomLevel.split(', ')
    wordList = []
    for level in levelTerms:
        wordList.extend(currentConfig[level.upper()])
    return wordList


def listToStringByComma(List):
    """
    Convert list to comma-separated string.

    Args:
        List: List of items to join

    Returns:
        str: Comma-separated string representation
    """
    return ', '.join(List)


def intListToStringByDash(List):
    """
    Convert list of integers to dash-separated string.

    Used for credit point ranges in configuration.

    Args:
        List: List of integers

    Returns:
        str: Dash-separated string (e.g., "3-6")
    """
    return '-'.join(str(x) for x in List)


def intStringToListByDash(String):
    """
    Parse dash-separated string to list of integers.

    Args:
        String: Dash-separated string (e.g., "3-6")

    Returns:
        list: List of integers
    """
    return list(map(int, String.split('-')))


def updateAIParams(data):
    """
    Update AI configuration parameters from form data.

    Processes admin form submission and updates all AI-related settings
    including model selection, API key, Bloom's verb lists, and credit
    point mappings. Persists changes to configuration file.

    Args:
        data: Form data dictionary containing all configuration values
    """
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


def createCSVofLOs(userID=-1):
    """
    Generate CSV export of units and learning outcomes.

    Creates a pandas DataFrame containing all units and their associated
    learning outcomes, formatted for CSV export. Can filter by user ID
    for personalized exports.

    Args:
        userID (int): User ID to filter units (-1 for all units)

    Returns:
        str: CSV-formatted string of units and outcomes
    """
    # Filter units based on user ID
    if userID != -1:
        units = Unit.query.filter_by(creatorid=current_user.id).all()
    else:
        units = Unit.query.all()

    # Create DataFrame with expected column structure
    df = pd.DataFrame(
        columns=[
            expectedIOFormatting["code"],
            expectedIOFormatting["title"],
            expectedIOFormatting["level"],
            expectedIOFormatting["CreditPoints"],
            expectedIOFormatting["Content"],
            expectedIOFormatting["Outcomes"]
        ])

    # Populate DataFrame with unit data
    for unit in units:
        # Concatenate learning outcomes with delimiters
        loString = ''
        for lo in unit.learning_outcomes:
            loString += lo.description + expectedIOFormatting["loAssessmentDelimiter"] + \
                        lo.assessment + expectedIOFormatting["loDelimiter"]

        # Add unit row to DataFrame
        df.loc[unit.id] = [
            unit.unitcode,
            unit.unitname,
            unit.level,
            unit.creditpoints,
            unit.description,
            loString
        ]

    # Convert to CSV string
    buf = io.StringIO()
    df.to_csv(buf)
    return buf.getvalue()


# ==================== LEARNING OUTCOME ROUTES ====================

@main.route('/create_lo/<int:unit_id>')
@login_required
def create_lo(unit_id):
    """
    Display learning outcome editor for a specific unit.

    Provides interface for creating, editing, reordering, and deleting
    learning outcomes. Includes Bloom's Taxonomy suggestions and AI evaluation.
    Access restricted to unit owner and admins.

    Args:
        unit_id: ID of the unit to edit outcomes for

    Returns:
        Rendered learning outcome editor template

    Raises:
        401: If user lacks permission
        404: If unit not found
    """
    # Check user permissions
    if current_user.role not in [UserType.ADMIN, UserType.UC]:
        abort(401)

    # Load unit and outcomes
    unit = Unit.query.get_or_404(unit_id)
    outcomes = unit.learning_outcomes if unit else []
    headings = ['#', 'Learning Outcome', 'Assessment', 'Delete', 'Reorder']

    return render_template(
        'create_lo.html',
        title=f'Creation Page',
        username=current_user.username,
        unit=unit,
        outcomes=outcomes,
        headings=headings,
        wordList=getBloomsWordList(unit.level)
    )


@main.delete("/lo_api/delete/<int:unit_id>/<int:lo_id>")
@login_required
def lo_delete(unit_id, lo_id):
    """
    API endpoint to delete a learning outcome.

    Removes a specific learning outcome from the database.
    Requires authentication.

    Args:
        unit_id: ID of the parent unit (for validation)
        lo_id: ID of the learning outcome to delete

    Returns:
        JSON response indicating success

    Raises:
        404: If learning outcome not found
    """
    lo = LearningOutcome.query.get_or_404(lo_id)
    db.session.delete(lo)
    db.session.commit()
    flash("Outcome deleted", "success")
    return jsonify({"ok": True})


@main.post("/lo_api/add/<int:unit_id>")
@login_required
def lo_add(unit_id):
    """
    API endpoint to add a new blank learning outcome.

    Creates a new empty learning outcome at the next available position
    for the specified unit. The outcome can then be edited inline.

    Args:
        unit_id: ID of the unit to add outcome to

    Returns:
        JSON response indicating success
    """
    unit = Unit.query.filter_by(id=unit_id).first()
    existing_los = LearningOutcome.query.filter_by(unit_id=unit_id).all()

    # Create blank outcome at next position
    blank_lo = LearningOutcome(
        unit_id=unit_id,
        position=len(existing_los) + 1,
        description=''
    )

    db.session.add(blank_lo)
    db.session.commit()
    flash("Outcome Added and Saved", "success")
    return jsonify({"ok": True})


@main.post("/lo_api/reorder/<int:unit_id>")
@login_required
def lo_reorder(unit_id):
    """
    API endpoint to reorder learning outcomes via drag-and-drop.

    Updates the position field for multiple learning outcomes based on
    the new order provided by the client. Uses bulk update for efficiency.

    Args:
        unit_id: ID of the unit containing the outcomes

    Request Body:
        JSON with 'order' array of outcome IDs in new sequence

    Returns:
        JSON response indicating success or error

    Raises:
        400: If order data is invalid or IDs don't match unit
    """
    data = request.get_json(force=True)
    order = data.get("order", [])
    unit_id = data.get("unit_id")

    # Validate order data
    if not order:
        return jsonify({"ok": False, "error": "empty order"}), 400

    # Verify all outcomes belong to the unit
    if unit_id is not None:
        count = LearningOutcome.query.filter(
            LearningOutcome.id.in_(order),
            LearningOutcome.unit_id == unit_id
        ).count()
        if count != len(order):
            return jsonify({"ok": False, "error": "ids mismatch for unit"}), 400

    # Create position mapping
    order = [int(x) for x in order]
    order_map = {lo_id: pos for pos, lo_id in enumerate(order, start=1)}

    # Bulk update positions
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
    """
    API endpoint to save all learning outcome edits.

    Batch saves changes to learning outcome descriptions and assessments.
    Expects data in position order matching existing outcomes.

    Args:
        unit_id: ID of the unit containing the outcomes

    Request Body:
        JSON object with position keys and [description, assessment] values

    Returns:
        JSON response indicating success
    """
    # Get existing outcomes in position order
    loList = LearningOutcome.query.filter_by(unit_id=unit_id).all()
    newLoDict = json.loads(request.data)

    # Update each outcome with new data
    # Assumes order received matches position order
    for lo, newLOData in zip(loList, newLoDict.values()):
        lo.description = newLOData[0]
        lo.assessment = newLOData[1]
        db.session.add(lo)

    db.session.commit()
    return jsonify({'status': 'ok'})


@main.get("/lo_api/export.csv/<int:unit_id>")
@login_required
def lo_export_csv(unit_id):
    """
    Export learning outcomes for a unit as CSV.

    Generates a CSV file containing all learning outcomes for the specified
    unit, including descriptions, assessments, and positions. File is named
    after the unit code for easy identification.

    Args:
        unit_id: ID of the unit to export outcomes from

    Returns:
        CSV file download response with appropriate headers

    Raises:
        404: If unit not found
    """
    unit = Unit.query.get_or_404(unit_id)
    rows = unit.learning_outcomes

    # Build CSV in memory
    import csv, io
    buf = io.StringIO()
    writer = csv.writer(buf)

    # Write header row
    writer.writerow(["#", "Description", "Assessment", "Position"])

    # Write outcome rows
    for i, lo in enumerate(rows, start=1):
        writer.writerow([i, lo.description, lo.assessment or "", lo.position])

    # Return as downloadable file
    out = buf.getvalue()
    return (out, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": f'attachment; filename="{unit.unitcode}_outcomes.csv"'
    })


@main.post("/lo_api/evaluate/<int:unit_id>")
@login_required
def ai_evaluate(unit_id):
    """
    AI evaluation endpoint for learning outcomes.

    Sends unit learning outcomes to the AI evaluation service for
    quality assessment based on Bloom's Taxonomy and best practices.
    Returns formatted evaluation results for display.

    Args:
        unit_id: ID of the unit to evaluate

    Returns:
        JSON response with evaluation HTML or error message

    Raises:
        404: If unit not found
        500: If evaluation service fails
    """
    unit = Unit.query.get_or_404(unit_id)
    rows = unit.learning_outcomes

    # Concatenate all outcome descriptions
    outcomes_text = "\n".join(lo.description for lo in rows)

    try:
        # Run AI evaluation
        result = run_eval(
            unit.level,
            unit.unitname,
            unit.creditpoints,
            outcomes_text
        )
        return jsonify({"ok": True, "html": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ==================== UNIT MANAGEMENT ROUTES ====================

@main.route('/search_unit', methods=['GET', 'POST'])
def search_unit():
    """
    Search and browse units with filtering and sorting.

    Provides a searchable, sortable list of units. Users can filter by
    unit code or name. Authenticated users see edit options for their units.

    Query Parameters:
        query: Search term
        filter: 'code' or 'name' (default: 'name')
        sort: 'unitcode' or 'unitlevel' (default: 'unitcode')

    Returns:
        Rendered search results template
    """
    if request.method == "GET":
        # Extract search parameters
        query = request.args.get("query", "").strip()
        filter_type = request.args.get("filter", "name")
        sort_by = request.args.get("sort", "unitcode")

        results = []

        if query:
            # Search by code or name
            if filter_type == "code":
                results = Unit.query.filter(Unit.unitcode.ilike(f"%{query}%")).all()
            else:
                results = Unit.query.filter(Unit.unitname.ilike(f"%{query}%")).all()
        else:
            # No query - fetch all units
            results = Unit.query.all()

        # Apply sorting
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
            sort_by=sort_by,
            can_edit=not current_user.is_anonymous
        )


@main.route('/view/<int:unit_id>', methods=['GET'])
def view(unit_id):
    """
    View detailed information for a specific unit.

    Displays unit details and learning outcomes. Provides navigation to
    edit functions for authorized users. Public route accessible to all.

    Args:
        unit_id: ID of the unit to view

    Returns:
        Rendered unit detail template

    Raises:
        404: If unit not found
    """
    if request.method == "GET":
        unit = Unit.query.filter_by(id=unit_id).first()
        if not unit:
            abort(404)
        return render_template(
            "view.html",
            title="Unit Details",
            unit=unit,
            UserType=UserType
        )


@main.route('/unit/<int:unit_id>/edit_unit', methods=['GET', 'POST'])
@login_required
def edit_unit(unit_id):
    """
    Edit unit details (code, name, level, credits, description).

    Allows unit owners and admins to modify unit properties.
    Validates uniqueness of unit codes and handles form submission.

    Args:
        unit_id: ID of the unit to edit

    GET:
        Display edit form with current values

    POST:
        Process form and update unit

    Returns:
        GET: Rendered edit form
        POST: Redirect to unit view on success

    Raises:
        401: If user lacks permission
        404: If unit not found
    """
    unit = Unit.query.filter_by(id=unit_id).first_or_404()
    form = EditUnitForm()

    # Check permissions
    if current_user.userType != UserType.ADMIN and unit.creatorid != current_user.id:
        abort(401)

    if request.method == "GET":
        # Populate form with current values
        form.unitcode.data = unit.unitcode
        form.unitname.data = unit.unitname
        form.level.data = unit.level
        form.creditpoints.data = unit.creditpoints
        form.description.data = unit.description
        return render_template("edit_unit.html", unit=unit, form=form)

    if request.method == "POST":
        data = request.form

        # Check unit code uniqueness
        unitcodeCheck = Unit.query.filter_by(
            unitcode=data["unitcode"].strip().upper()
        ).first()

        if unitcodeCheck != None and unitcodeCheck.id != unit.id:
            flash("That unit code already exists. Please choose a different one.", "danger")
            return render_template("edit_unit.html", unit=unit, form=form)

        # Update unit fields
        unit.unitcode = data["unitcode"].strip().upper()
        unit.unitname = data["unitname"].strip()
        unit.level = int(data["level"])
        unit.creditpoints = int(data["creditpoints"])
        unit.description = data["description"].strip()

        db.session.commit()
        flash("Unit updated successfully!", "success")
        return redirect(url_for("main.view", unit_id=unit.id))


@main.route('/new_unit', methods=['GET', 'POST'])
@login_required
def new_unit():
    """
    Create a new academic unit.

    Provides form for unit coordinators and admins to create new units.
    Validates unit code uniqueness and sets the creator as owner.

    GET:
        Display unit creation form

    POST:
        Process form and create unit

    Returns:
        GET: Rendered creation form
        POST: Redirect to dashboard on success

    Raises:
        401: If user lacks permission
    """
    # Check permissions
    if current_user.role not in [UserType.ADMIN, UserType.UC]:
        abort(401)

    form = NewUnitForm()

    if request.method == 'GET':
        return render_template(
            'new_unit_form.html',
            title=f'Create New Unit',
            username=current_user.username,
            form=form
        )

    if request.method == 'POST':
        # Validate form
        if not form.validate():
            return render_template(
                'new_unit_form.html',
                title=f'Create New Unit',
                username=current_user.username,
                form=form
            )

        data = request.form

        # Check unit code uniqueness
        unitcodeCheck = db.session.query(Unit).filter_by(
            unitcode=data["unitcode"]
        ).first()

        if unitcodeCheck != None:
            flash("Unit already Exists", 'error')
            return redirect("/new_unit")

        # Create new unit
        newUnit = Unit(
            unitcode=data["unitcode"],
            unitname=data["unitname"],
            level=data["level"],
            creditpoints=data["creditpoints"],
            description=data["description"],
            creatorid=current_user.id
        )

        db.session.add(newUnit)
        db.session.commit()
        flash("Unit Created", 'success')
        return redirect("/main_page")


@main.route('/delete_unit/<int:unit_id>', methods=['DELETE'])
@login_required
def delete_unit(unit_id):
    """
    API endpoint to delete a unit and all its learning outcomes.

    Restricted to unit owner and admins. Cascades delete to all
    associated learning outcomes.

    Args:
        unit_id: ID of the unit to delete

    Returns:
        JSON response indicating success

    Raises:
        401: If user lacks permission
        404: If unit not found
    """
    unit = Unit.query.filter_by(id=unit_id).first_or_404()

    # Check permissions
    if current_user.userType != UserType.ADMIN and unit.creatorid != current_user.id:
        abort(401)

    if request.method == 'DELETE':
        db.session.delete(unit)
        db.session.commit()
        flash("Unit Deleted", 'success')
        return jsonify({"ok": True})


# ==================== IMPORT/EXPORT ROUTES ====================

# Expected format for CSV import/export
expectedIOFormatting = {
    # Implemented fields
    'code': 'code',
    'title': 'title',
    'level': 'level',
    'Outcomes': 'Outcomes',
    'CreditPoints': 'CreditPoints',

    # Unimplemented fields (for future expansion)
    'Assessments': 'Assessments',
    'Faculty': 'Faculty',
    'ROE': 'ROE',
    'UnitType': 'UnitType',
    'Curriculum': 'Curriculum',
    'Content': 'Content',

    # Delimiters for parsing
    'loDelimiter': '|*|',
    'loAssessmentDelimiter': '|',
}


@main.route('/import-units', methods=['POST'])
@login_required
def import_units():
    """
    Import units from CSV or Excel file.

    Processes uploaded file containing unit data and learning outcomes.
    Validates data format, checks for duplicates, and creates units with
    their associated outcomes. Supports both AJAX and standard requests.

    File Format:
        CSV or XLSX with columns: code, title, level, Outcomes
        Outcomes use special delimiters for multiple values

    Returns:
        JSON response for AJAX requests
        Redirect with flash message for standard requests

    Error Handling:
        - Missing file
        - Invalid format
        - Missing required columns
        - Duplicate unit codes
    """
    # Check request type
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Get uploaded file
    file = request.files.get("import_file")
    if not file:
        if is_ajax:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        flash("No file uploaded", "danger")
        return redirect(url_for("main.main_page"))

    # Process file based on type
    try:
        if file.filename.endswith(('xlsx', 'xls')):
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file)
    except Exception as e:
        error_msg = f"Failed to read file: {str(e)}"
        if is_ajax:
            return jsonify({'success': False, 'message': error_msg}), 400
        flash(error_msg, "danger")
        return redirect(url_for("main.main_page"))

    # Validate required columns
    required_headers = [
        expectedIOFormatting['code'],
        expectedIOFormatting['title'],
        expectedIOFormatting['level'],
        expectedIOFormatting['Outcomes']
    ]

    missing_headers = [h for h in required_headers if h not in df.columns]
    if missing_headers:
        error_msg = f"Missing required columns: {', '.join(missing_headers)}. Please try again."
        if is_ajax:
            return jsonify({'success': False, 'message': error_msg}), 400
        flash(error_msg, "danger")
        return redirect(url_for("main.main_page"))

    # Process data
    unitcount = 0
    hasDuplicates = False
    dupCount = 0
    hasLacksUnitCode = False
    codeCount = 0

    for _, newUnit in df.iterrows():
        # Skip units without code
        if pd.isna(newUnit[expectedIOFormatting['code']]):
            hasLacksUnitCode = True
            codeCount += 1
            continue

        # Check for duplicates
        unitcodeCheck = db.session.query(Unit).filter_by(
            unitcode=str(newUnit[expectedIOFormatting['code']]).strip()
        ).first()

        if unitcodeCheck != None:
            hasDuplicates = True
            dupCount += 1
            continue

        # Create unit
        dbUnit = Unit(
            unitcode=str(newUnit[expectedIOFormatting['code']]).strip(),
            unitname=newUnit[expectedIOFormatting['title']],
            level=newUnit[expectedIOFormatting['level']],
            description=newUnit[expectedIOFormatting['Content']],
            creatorid=current_user.id
        )
        db.session.add(dbUnit)
        db.session.flush()
        unitcount += 1

        # Process learning outcomes
        loPos = 1
        for lo in str(newUnit.Outcomes).split(expectedIOFormatting['loDelimiter']):
            loAsm = lo.split(expectedIOFormatting['loAssessmentDelimiter'])
            lo = loAsm[0]
            asm = loAsm[1] if len(loAsm) == 2 else ''

            if lo == '':
                continue

            dbLO = LearningOutcome(
                unit_id=dbUnit.id,
                position=loPos,
                description=lo,
                assessment=asm
            )
            db.session.add(dbLO)
            loPos += 1

    db.session.commit()

    # Build result message
    msg = f"{unitcount} units added successfully from file. "
    if hasLacksUnitCode:
        msg += f"{codeCount} units lacked a unitcode and were skipped. "
    if hasDuplicates:
        msg += f"{dupCount} units were duplicates and were skipped. "

    if is_ajax:
        return jsonify({'success': True, 'message': msg, 'units_added': unitcount})

    flash(msg, "success")
    return redirect(url_for("main.main_page"))


@main.route('/export_my_units')
@login_required
def export_my_units():
    """
    Export current user's units as CSV.

    Generates downloadable CSV containing all units created by the
    current user, including learning outcomes and assessments.

    Returns:
        CSV file download response
    """
    out = createCSVofLOs(current_user.id)
    return (out, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="units_and_outcomes.csv"'
    })


@main.route('/export_all_units')
@login_required
def export_all_units():
    """
    Export all units in the system as CSV.

    Admin function to export all units regardless of creator.
    Useful for backups and system-wide analysis.

    Returns:
        CSV file download response
    """
    out = createCSVofLOs()
    return (out, 200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="units_and_outcomes.csv"'
    })


# ==================== ADMIN ROUTES ====================

@main.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    """
    Admin configuration panel for AI and system settings.

    Allows admins to configure:
    - AI model selection and API keys
    - Bloom's Taxonomy verb lists
    - Credit point to outcome mappings
    - Taxonomy level names

    GET:
        Display configuration form with current values

    POST:
        Update configuration and persist to file

    Returns:
        GET: Rendered admin panel
        POST: Redirect with success message

    Raises:
        401: If user is not admin
    """
    # Check admin permission
    if current_user.userType != UserType.ADMIN:
        flash("You do not have permission to access that page.", "danger")
        return redirect(url_for("main.home"))

    form = AdminForm()

    if request.method == 'GET':
        # Load current configuration
        loadconfig = config_manager.getCurrentParams()

        # Convert lists to strings for form display
        loadconfig["6 Points"] = intListToStringByDash(loadconfig["6 Points"])
        loadconfig["12 Points"] = intListToStringByDash(loadconfig["12 Points"])
        loadconfig["24 Points"] = intListToStringByDash(loadconfig["24 Points"])

        # Populate form fields
        form.knowledge.data = listToStringByComma(loadconfig['KNOWLEDGE'])
        form.comprehension.data = listToStringByComma(loadconfig['COMPREHENSION'])
        form.application.data = listToStringByComma(loadconfig['APPLICATION'])
        form.analysis.data = listToStringByComma(loadconfig['ANALYSIS'])
        form.synthesis.data = listToStringByComma(loadconfig['SYNTHESIS'])
        form.evaluation.data = listToStringByComma(loadconfig['EVALUATION'])
        form.banned.data = listToStringByComma(loadconfig['BANNED'])

        return render_template(
            'admin_page_template.html',
            form=form,
            config=loadconfig,
            getattr=getattr
        )

    if request.method == 'POST':
        # Validate form
        if not form.validate():
            flash("Failed To Validate Form.", 'error')
            return redirect('admin')

        # Update configuration
        updateAIParams(request.form)
        flash("Settings Successfully Updated.", 'success')
        return redirect('admin')


@main.route('/AI_reset', methods=['POST'])
@login_required
def AI_reset():
    """
    Reset AI configuration to default values.

    Admin-only endpoint to restore all configuration settings to
    their default values from AIConfigDefault.json.

    Returns:
        JSON response indicating success or failure

    Raises:
        401: If user is not admin
        500: If reset fails
    """
    # Check admin permission
    if current_user.userType != UserType.ADMIN:
        return "Unauthorised", 401

    if request.method == 'POST':
        if request.data == b'Reset':
            config_manager.resetParamsToDefault()
            flash("Settings Successfully Reset to Default.", 'success')
            return jsonify({'status': 'ok'})
        return "Failed To Reset To Default", 500


# ==================== INFORMATIONAL ROUTES ====================

@main.route('/help')
def help_page():
    """
    Display help and documentation page.

    Provides comprehensive user documentation for all features
    and user types. Includes tutorials and FAQs.

    Returns:
        Rendered help page template
    """
    return render_template('help_page.html')


@main.route('/bloom-guide')
def bloom_guide():
    """
    Display Bloom's Taxonomy guide with current configuration.

    Shows the taxonomy levels, associated verbs, and credit point
    mappings currently configured in the system. Interactive guide
    for understanding learning outcome requirements.

    Returns:
        Rendered Bloom's guide template with configuration
    """
    # Get current AI configuration
    config = config_manager.getCurrentParams()

    # Process credit points for template
    config['6_Points_Min'] = config['6 Points'][0]
    config['6_Points_Max'] = config['6 Points'][1]
    config['12_Points_Min'] = config['12 Points'][0]
    config['12_Points_Max'] = config['12 Points'][1]
    config['24_Points_Min'] = config['24 Points'][0]
    config['24_Points_Max'] = config['24 Points'][1]

    # Convert to JSON for JavaScript
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

    return render_template(
        'bloom_guide.html',
        config=config,
        config_json=json.dumps(config_json)
    )

