from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, EqualTo
from enum import Enum

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirmpassword = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    usertype = SelectField('User Type', choices=[('unit_coordinator', 'Unit Coordinator'), ('guest', 'Guest'), ('admin', 'Admin')])
    submit = SubmitField('Sign Up')

class NewUnitForm(FlaskForm):
    unitcode = StringField('Unit Code', validators=[DataRequired()])
    unitname = StringField('Unit Name', validators=[DataRequired()])
    level = SelectField('Level', choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6'),])
    creditpoints = SelectField('Credit Points', choices=[(6, '6'),(12, '12'), (24, '24')])
    description = TextAreaField('Unit Description')
    submit = SubmitField('Create Unit')

