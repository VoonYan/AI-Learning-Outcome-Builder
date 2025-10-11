"""
WTForms definitions for all application forms.

This module defines Flask-WTF forms used throughout the application,
including authentication forms, unit management forms, and admin configuration.
All forms include CSRF protection automatically via Flask-WTF.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Regexp
from . import config_manager


class LoginForm(FlaskForm):
    """
    User login form with username/password authentication.

    Fields:
        username: Required username field
        password: Required password field  
        remember_me: Optional checkbox for persistent sessions
        submit: Form submission button
    """
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')


class SignupForm(FlaskForm):
    """
    User registration form for creating new accounts.

    Fields:
        username: Required unique username
        password: Required password
        confirmpassword: Password confirmation (must match password)
        usertype: Role selection (Unit Coordinator or Admin)
        submit: Form submission button

    Validation:
        - Password and confirm password must match
        - All fields are required
    """
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirmpassword = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')]
    )
    usertype = SelectField(
        'User Type',
        choices=[('unit_coordinator', 'Unit Coordinator'), ('admin', 'Admin')]
    )
    submit = SubmitField('Sign Up')


class NewUnitForm(FlaskForm):
    """
    Form for creating a new academic unit.

    Fields:
        unitcode: Unit identifier (e.g., "CITS3001")
        unitname: Full name of the unit
        level: Academic level (1-6)
        creditpoints: Credit value (6, 12, or 24 points)
        description: Optional detailed description
        submit: Form submission button
    """
    unitcode = StringField('Unit Code', validators=[DataRequired()])
    unitname = StringField('Unit Name', validators=[DataRequired()])
    level = SelectField(
        'Level',
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6')]
    )
    creditpoints = SelectField(
        'Credit Points',
        choices=[(6, '6'), (12, '12'), (24, '24')]
    )
    description = TextAreaField('Unit Description')
    submit = SubmitField('Create Unit')


class EditUnitForm(FlaskForm):
    """
    Form for editing existing unit details.

    Identical to NewUnitForm but with different submit button text.
    Used when modifying already created units.

    Fields:
        unitcode: Unit identifier (can be modified)
        unitname: Full name of the unit
        level: Academic level (1-6)
        creditpoints: Credit value (6, 12, or 24 points)
        description: Optional detailed description
        submit: Save changes button
    """
    unitcode = StringField('Unit Code', validators=[DataRequired()])
    unitname = StringField('Unit Name', validators=[DataRequired()])
    level = SelectField(
        'Level',
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'), (6, '6')]
    )
    creditpoints = SelectField(
        'Credit Points',
        choices=[(6, '6'), (12, '12'), (24, '24')]
    )
    description = TextAreaField('Unit Description')
    submit = SubmitField('Save')


class AdminForm(FlaskForm):
    """
    Admin configuration form for AI and Bloom's Taxonomy settings.

    This form allows administrators to configure:
    - AI model selection and API keys
    - Bloom's Taxonomy verb lists for each cognitive level
    - Banned words that shouldn't appear in learning outcomes
    - Credit point ranges for outcome counts
    - Taxonomy level mappings

    Fields:
        model: AI model selection dropdown
        apikey: API key for AI service
        knowledge-evaluation: Verb lists for Bloom's levels
        banned: Words to exclude from outcomes
        level1-6: Names for each taxonomy level
        cp6/12/24: Outcome count ranges for credit points

    Note: Model choices are dynamically loaded from config
    """
    # Load current configuration for model choices
    currConfig = config_manager.getCurrentParams()
    modelPairs = []
    for model in currConfig["available_models"]:
        # Format model names for display (capitalize and remove version)
        modelPairs.append((model, model.replace('-', ' ').capitalize()[:-3]))

    # AI Configuration fields
    model = SelectField('AI Model', choices=(modelPairs), id="modelSelect")
    apikey = StringField('API Key', validators=[DataRequired()], id="apiKey")

    # Bloom's Taxonomy verb lists for each cognitive level
    # Each field contains comma-separated verb lists
    knowledge = TextAreaField('Knowledge', validators=[DataRequired()], id="knowledgeList")
    comprehension = TextAreaField('Comprehension', validators=[DataRequired()], id="comprehensionList")
    application = TextAreaField('Application', validators=[DataRequired()], id="applicationList")
    analysis = TextAreaField('Analysis', validators=[DataRequired()], id="analysisList")
    synthesis = TextAreaField('Synthesis', validators=[DataRequired()], id="synthesisList")
    evaluation = TextAreaField('Evaluation', validators=[DataRequired()], id="evaluationList")

    # Banned words configuration
    banned = TextAreaField('Words to Exclude', validators=[DataRequired()], id="bannedList")

    # Taxonomy level naming configuration
    level1 = StringField('Level 1', validators=[DataRequired()], id="level1Tax")
    level2 = StringField('Level 2', validators=[DataRequired()], id="level2Tax")
    level3 = StringField('Level 3', validators=[DataRequired()], id="level3Tax")
    level4 = StringField('Level 4', validators=[DataRequired()], id="level4Tax")
    level5 = StringField('Level 5', validators=[DataRequired()], id="level5Tax")
    level6 = StringField('Level 6', validators=[DataRequired()], id="level6Tax")

    # Credit point to outcome count mapping
    # Format: "min-max" (e.g., "3-6" means 3 to 6 outcomes)
    cp6 = StringField(
        '6 Credit Points',
        validators=[
            DataRequired(),
            Regexp(r'^\d{1,2}-\d{1,2}$', message='Must use format [number]-[number]')
        ],
        id="cp6Num"
    )
    cp12 = StringField(
        '12 Credit Points',
        validators=[
            DataRequired(),
            Regexp(r'^\d{1,2}-\d{1,2}$', message='Must use format [number]-[number]')
        ],
        id="cp12Num"
    )
    cp24 = StringField(
        '24 Credit Points',
        validators=[
            DataRequired(),
            Regexp(r'^\d{1,2}-\d{1,2}$', message='Must use format [number]-[number]')
        ],
        id="cp24Num"
    )