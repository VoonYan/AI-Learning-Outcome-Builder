from flask import render_template
from app.blueprints import main as flaskApp

@flaskApp.route('/')
def mainfunc():
    return "<h1>Hello World</h1>"

@flaskApp.route('/user/<name>')
def user(name):
    return "<h1>Hello {}</h1>".format(name)

@flaskApp.route('/indexes')
def index():
    user = {'username': 'Akshay'}
    return render_template('test_page.html', title='Home', user=user)