from flask import render_template, redirect, url_for, flash, request, session, Blueprint,jsonify
from flask_login import current_user, login_required
from .forms import NewUnitForm
from . import db
from .models import db, Unit, LearningOutcome
from . import create_app
from sqlalchemy import case, update

main = Blueprint('main', __name__)


@main.route('/main-page')
@main.route('/')
@login_required
def main_page(): 
    return render_template('main_page.html', title=f'{current_user.username} Dashboard', username=current_user.username)

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

    # ensure all ids belong to the same unit if unit_id is provided
    if unit_id is not None:
        count = LearningOutcome.query.filter(
            LearningOutcome.id.in_(order),
            LearningOutcome.unit_id == unit_id
        ).count()
        if count != len(order):
            return jsonify({"ok": False, "error": "ids mismatch for unit"}), 400

    # Build a CASE expression to bulk update positions in one commit
    # Order is 1..N in the order received from the client
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

@main.route('/unit-search')
@login_required
def search_units():
    return render_template('search_unit.html', title=f'Creation Page', username=current_user.username)

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
