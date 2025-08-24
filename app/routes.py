from flask import render_template, redirect, url_for, flash, session
from app.blueprints import main as flaskApp
from app.forms import LoginForm


@flaskApp.route('/login-page', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        session['username'] = username # store in session
        return redirect(url_for('main.main_page'))
    return render_template('login_form2.html', title='Sign In', form=form)


@flaskApp.route('/main-page')
def main_page(): 
    username = session.get('username')
    if not username:
        return redirect(url_for('main.login_page'))
    return render_template('main_page.html', title=f'{username} Dashboard', username=username)

@flaskApp.route('/base')
def base_main(): 
    username = session.get('username')
    if not username:
        return redirect(url_for('main.login_page'))
    return render_template('base_main.html', title=f'{username} Dashboard', username=username)

@flaskApp.route('/create-lo')
def create_lo():
    username = session.get('username')
    if not username:
        return redirect(url_for('main.login_page'))
    return render_template('create_lo.html', title=f'Creation Page', username=username)