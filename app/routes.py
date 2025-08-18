from flask import render_template
from app.blueprints import main as flaskApp
from app.forms import LoginForm

@flaskApp.route('/')
def mainfunc():
    return "<h1>Hello World</h1>"

@flaskApp.route('/user/<name>')
def user(name):
    return "<h1>Hello {}</h1>".format(name)

@flaskApp.route('/indexes/<username>')
def index(username):
    return render_template('test_page.html', title=f'Welcome {username}', username=username)

@flaskApp.route('/login-form')
def login_form():
    form = LoginForm()
    return render_template('login_form.html', title='Sign In', form=form)