from flask import render_template, redirect, url_for, flash, request, session, Blueprint
from flask_login import current_user, login_required
from .forms import NewUnitForm
from . import db
from .models import Unit
from . import config_manager


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
    headings = ['#', 'Learning Outcome', 'How will each outcome be assessed', 'Delete', 'Reorder']
    return render_template('create_lo.html', title=f'Creation Page', username=current_user.username, headings=headings)

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
