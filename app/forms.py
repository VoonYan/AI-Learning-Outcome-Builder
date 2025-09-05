from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, EqualTo
from . import config_manager

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

class AdminForm(FlaskForm):
    currConfig = config_manager.getCurrentParams()
    modelPairs = []
    for model in currConfig["available_models"]:
        modelPairs.append((model, model.replace('-', ' ').capitalize()[:-3]))
    
    model = SelectField('AI Model', choices=(modelPairs), id="modelSelect")
    apikey = StringField('API Key', validators=[DataRequired()], id="apiKey")

    knowledge = TextAreaField('Knowledge', validators=[DataRequired()], id="knowledgeList")
    comprehension = TextAreaField('Comprehension', validators=[DataRequired()], id="comprehensionList")
    application =  TextAreaField('Application', validators=[DataRequired()], id="applicationList")
    analysis =  TextAreaField('Analysis', validators=[DataRequired()], id="analysisList")
    synthesis =  TextAreaField('Synthesis', validators=[DataRequired()], id="synthesisList")
    evaluation =  TextAreaField('Evaluation', validators=[DataRequired()], id="evaluationList")
    banned =  TextAreaField('Words to Exclude', validators=[DataRequired()], id="bannedList")
    level1 =  StringField('Level 1', validators=[DataRequired()], id="level1Tax")
    level2 =  StringField('Level 2', validators=[DataRequired()], id="level2Tax")
    level3 =  StringField('Level 3', validators=[DataRequired()], id="level3Tax")
    level4 =  StringField('Level 4', validators=[DataRequired()], id="level4Tax")
    level5 =  StringField('Level 5', validators=[DataRequired()], id="level5Tax")
    level6 =  StringField('Level 6', validators=[DataRequired()], id="level6Tax")
    cp6 =  StringField('6 Credit Points', validators=[DataRequired()], id="cp6Num")
    cp12 =  StringField('12 Credit Points', validators=[DataRequired()], id="cp12Num")
    cp24 =  StringField('24 Credit Points', validators=[DataRequired()], id="cp24Num")

