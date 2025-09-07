from flask import render_template, redirect, url_for, request, flash, Blueprint
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from .forms import LoginForm, SignupForm
from .models import User, UserType
from . import db

auth = Blueprint("auth", __name__)
#using a seperate file for user management as it will have 3 routes for this one purpose, login, signup and logout

@auth.route('/login_page', methods = ['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        form = LoginForm()
        return render_template('login_form2.html', title='Sign In', form=form)
    
    if request.method == 'POST':
        data = request.form
        userDB = User.query.filter_by(username=data['username']).first()

        if userDB == None or check_password_hash(userDB.password_hash, data["password"]) == False:
            flash("Login Failed. Double Check Your Details And Try Again.", 'error')
            return redirect("/login_page")
        else:
            login_user(userDB, remember=True)
            return redirect("/main_page")


@auth.route('/signup_page', methods = ['GET', 'POST'])
def signup_page():
    form = SignupForm()
    if request.method == 'GET':
        return render_template('signup_form.html', title='Sign Up', form=form)
    if request.method == 'POST':
        if not form.validate():
            return render_template('signup_form.html', form=form)
        
        data = request.form
        userDB = User.query.filter_by(username=data['username']).first()
        if userDB is not None:
            flash("Username Already In Use", 'error')
            return redirect('/signup_page')
        else:
            hashedPassword= generate_password_hash(data["password"])
            newUser = User(username=data["username"], password_hash=hashedPassword, userType=UserType(data['usertype']).name)
            db.session.add(newUser)
            db.session.commit()
            flash("Account Created", 'success')
            return redirect("/login_page")


@auth.route('/Logout')
def Logout():
    logout_user()
    return redirect("/main_page")
