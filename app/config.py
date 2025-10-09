"""
Configuration classes for the AI Learning Outcome Builder Flask application.

This module provides different configuration settings for various environments:
- Development: Debug mode enabled with auto-reload
- Testing: In-memory database for unit tests
- Deployment: Production settings with SQLite database
"""

import os

# Get the absolute path of the application directory
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """
    Base configuration class with settings common to all environments.

    Attributes:
        SECRET_KEY: Secret key for session encryption and CSRF protection
    """
    # Secret key for Flask sessions and CSRF protection
    # Defaults to 'default_secret_key' if environment variable not set
    SECRET_KEY = os.environ.get('AI_BUILDER_KEY', 'default_secret_key')


class DeploymentConfig(Config):
    """
    Production deployment configuration.

    Uses SQLite database file stored in the application directory.
    Debug mode is disabled for security.
    """
    # SQLite database file location for production
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')


class TestingConfig(Config):
    """
    Configuration for unit testing.

    Uses in-memory SQLite database that doesn't persist between tests.
    Testing flag enabled for test-specific behavior.
    """
    # In-memory database for isolated testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///memory'

    # Enable testing mode
    TESTING = True


class DevelopmentConfig(Config):
    """
    Development environment configuration.

    Enables debug mode for detailed error messages and auto-reload.
    Templates auto-reload on changes for faster development.
    """
    # SQLite database file for development
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')

    # Enable debug mode for development
    DEBUG = True

    # Auto-reload templates when they change
    TEMPLATES_AUTO_RELOAD = True

    # Development-specific secret key
    SECRET_KEY = os.environ.get('SECRET_KEY', 'development-secret-key')