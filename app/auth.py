"""
Authentication module for user login, signup, and logout functionality.

This module handles all authentication-related routes using Flask-Login
for session management and Werkzeug for secure password hashing.
Provides endpoints for user registration, login, and logout operations.
"""

from flask import render_template, redirect, url_for, request, flash, Blueprint
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from .forms import LoginForm, SignupForm
from .models import User, UserType
from . import db

# Create authentication blueprint for modular route organization
auth = Blueprint("auth", __name__)


@auth.route('/login_page', methods=['GET', 'POST'])
def login_page():
    """
    Handle user login page and authentication.

    GET: Display the login form
    POST: Process login credentials and authenticate user

    Authentication process:
    1. Verify username exists in database
    2. Check password hash matches stored hash
    3. Create user session on successful authentication
    4. Redirect to dashboard or show error message

    Returns:
        GET: Rendered login form template
        POST: Redirect to dashboard on success or login page with error
    """
    if request.method == 'GET':
        # Create and display login form
        form = LoginForm()
        return render_template('login_form2.html', title='Sign In', form=form)

    if request.method == 'POST':
        # Extract form data
        data = request.form

        # Query database for user by username
        userDB = User.query.filter_by(username=data['username']).first()

        # Validate credentials
        if userDB == None or check_password_hash(userDB.password_hash, data["password"]) == False:
            # Invalid username or password
            flash("Login Failed. Double Check Your Details And Try Again.", 'error')
            return redirect("/login_page")
        else:
            # Successful authentication - create session
            # remember=True keeps user logged in across browser sessions
            login_user(userDB, remember=True)
            return redirect("/dashboard")


@auth.route('/signup_page', methods=['GET', 'POST'])
def signup_page():
    """
    Handle user registration page and account creation.

    GET: Display the signup form
    POST: Process registration and create new user account

    Registration process:
    1. Validate form data (passwords match, valid input)
    2. Check username uniqueness
    3. Hash password for secure storage
    4. Create new user record in database
    5. Redirect to login page for immediate access

    User types available:
    - Unit Coordinator: Can create and manage their own units
    - Admin: Full system access including configuration

    Returns:
        GET: Rendered signup form template
        POST: Redirect to login on success or signup page with error
    """
    form = SignupForm()

    if request.method == 'GET':
        # Display registration form
        return render_template('signup_form.html', title='Sign Up', form=form)

    if request.method == 'POST':
        # Validate form fields (passwords match, required fields)
        if not form.validate():
            # Re-display form with validation errors
            return render_template('signup_form.html', form=form)

        # Extract form data
        data = request.form

        # Check if username already exists
        userDB = User.query.filter_by(username=data['username']).first()
        if userDB is not None:
            # Username taken - show error and redirect
            flash("Username Already In Use", 'error')
            return redirect('/signup_page')
        else:
            # Create new user account
            # Hash password for security (uses Werkzeug's bcrypt by default)
            hashedPassword = generate_password_hash(data["password"])

            # Create user object with selected role
            newUser = User(
                username=data["username"],
                password_hash=hashedPassword,
                userType=UserType(data['usertype']).name
            )

            # Save to database
            db.session.add(newUser)
            db.session.commit()

            # Show success message and redirect to login
            flash("Account Created", 'success')
            return redirect("/login_page")


@auth.route('/logout')
def logout():
    """
    Handle user logout and session termination.

    Clears the user session and redirects to home page.
    Flask-Login handles session cleanup automatically.

    Returns:
        Redirect to home page with logout confirmation
    """
    # Clear user session
    logout_user()

    # Show logout confirmation
    flash("Logged out.", "success")

    # Redirect to public home page
    return redirect("/home")
