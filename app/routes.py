from flask import render_template, redirect, url_for, flash, request, session, Blueprint, jsonify
from flask_login import current_user, login_required
from .forms import NewUnitForm, AdminForm
from . import db
from .models import Unit, UserType
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
    