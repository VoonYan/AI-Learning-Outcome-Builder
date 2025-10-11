"""
AI Learning Outcome Builder - Flask Application Initialization Module

This module initializes and configures the Flask application for the AI Learning
Outcome Builder system. It sets up core components including database connections,
authentication, configuration management, and blueprint registration.

Core Components:
    - Flask application factory pattern
    - SQLAlchemy database initialization
    - Flask-Migrate for database migrations
    - Flask-Login for authentication
    - Configuration manager for AI settings
    - Blueprint registration for modular routing

Application Structure:
    The application uses the factory pattern to create Flask instances with
    different configurations (Development, Testing, Production). This allows
    for easy testing and deployment flexibility.

Database:
    Uses SQLite by default with automatic database creation if missing.
    Supports migrations through Flask-Migrate for schema updates.

Authentication:
    Flask-Login manages user sessions with redirect to login page for
    protected routes. User loader callback fetches user objects from database.

Configuration:
    AI configuration managed through thread-safe ConfigManager class.
    Supports dynamic updates to AI models, Bloom's taxonomy settings, and
    evaluation parameters.

Attributes:
    db: SQLAlchemy database instance
    migrate: Flask-Migrate instance for database migrations
    login_manager: Flask-Login manager for authentication
    config_manager: Thread-safe AI configuration manager

Functions:
    load_user: Callback to load user objects for Flask-Login
    create_app: Application factory function
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from .config import DevelopmentConfig, TestingConfig
from werkzeug.security import generate_password_hash
import os
from .ai_handler import ConfigManager

# Initialize Flask extensions
# These are initialized here and attached to app in create_app()
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# Set the login view for authentication redirects
# When @login_required is used, redirect here if not authenticated
login_manager.login_view = 'auth.login_page'

# Initialize configuration manager with AI settings
# Thread-safe manager for AI evaluation parameters
config_manager = ConfigManager('app/AIConfig.json')


@login_manager.user_loader
def load_user(user_id):
    """
    Flask-Login user loader callback.

    This callback is used by Flask-Login to reload the user object from
    the user ID stored in the session. It runs before every request when
    a user is logged in.

    Args:
        user_id (str): User ID from session (converted to int internally)

    Returns:
        User: User object if found, None otherwise

    Note:
        Returning None will treat the user as logged out
    """
    from .models import User
    return User.query.get(int(user_id))


def create_app(config=DevelopmentConfig):
    """
    Application factory function using Flask factory pattern.

    Creates and configures a Flask application instance with the specified
    configuration. Sets up database, migrations, authentication, and
    registers blueprints. Ensures database exists and adds cache control
    headers to prevent browser caching issues.

    Args:
        config: Configuration class (DevelopmentConfig, TestingConfig, 
                or DeploymentConfig). Defaults to DevelopmentConfig.

    Returns:
        Flask: Configured Flask application instance

    Configuration Classes:
        - DevelopmentConfig: Debug enabled, auto-reload templates
        - TestingConfig: In-memory database for unit tests
        - DeploymentConfig: Production settings with file-based database

    Database Initialization:
        Automatically creates app.db if it doesn't exist. This prevents
        errors on first run and after git operations that might exclude
        the database file.

    Cache Control:
        Adds headers to all responses to prevent aggressive browser caching
        which can cause issues during development when files change frequently.

    Blueprints:
        - main: All application routes except authentication
        - auth: Login, logout, and registration routes
    """
    # Create Flask instance
    flaskApp = Flask(__name__)
    config_name = os.getenv("FLASK_CONFIG", "Development")
    if config_name == 'testing':
        flaskApp.config.from_object(TestingConfig)
    else:
        flaskApp.config.from_object(config)
    db.init_app(flaskApp)  
    migrate.init_app(flaskApp, db, render_as_batch=True)

    # Initialize login manager
    login_manager.init_app(flaskApp)

    # Register blueprints for modular routing
    # Main blueprint: unit management, learning outcomes, admin functions
    from .routes import main
    # Auth blueprint: login, logout, registration
    from .auth import auth

    flaskApp.register_blueprint(main)
    flaskApp.register_blueprint(auth)

    # Database initialization check
    # app.db can get corrupted in git merges so it's in .gitignore
    # This code checks if app.db exists and creates it if missing
    appdbPath = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        'app.db'
    )

    if os.path.exists(appdbPath) == False:
        # Create all tables if database doesn't exist
        with flaskApp.app_context():
            db.create_all()
            db.session.commit()
    
    if config_name == 'testing':
        with flaskApp.app_context():
            from app.models import User, Unit, UserType
            db.create_all()
            db.session.add(
                User(
                    username='admin',
                    password_hash=generate_password_hash("password"),
                    userType=UserType('admin').name
                )
            )
            db.session.add(
                Unit(
                    unitcode= 'CITS3200', 
                    unitname= 'Professional Computing', 
                    level= 3, 
                    creditpoints= 6, 
                    description= 'description for testing',
                    creatorid = 1
                )
            )
            db.session.commit()
    
            
    @flaskApp.after_request
    def add_header(response):
        """
        Add cache control headers to prevent browser caching.

        Prevents browsers from caching responses which can cause
        issues during development when files change frequently.
        Especially important for JavaScript and CSS files.

        Args:
            response: Flask response object

        Returns:
            response: Modified response with no-cache headers

        Headers Added:
            - Cache-Control: Prevents all caching
            - Pragma: HTTP/1.0 backward compatibility
            - Expires: Sets expiry to past date
        """
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    return flaskApp