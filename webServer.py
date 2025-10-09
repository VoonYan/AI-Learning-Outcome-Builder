"""
Production web server entry point for the AI Learning Outcome Builder.

This module serves as the production entry point for running the Flask application
with deployment configuration. It creates the Flask app instance with production
settings and can be used by WSGI servers like Gunicorn or uWSGI.

Usage:
    Development: Use 'flask run' command instead of this file
    Production: python webServer.py or use with WSGI server

Note: The recommended way to run in development is using 'flask run' command
      which provides better debugging and auto-reload capabilities.
"""

from app import create_app
from app.config import DeploymentConfig

# Create Flask application instance with production configuration
# DeploymentConfig uses SQLite database and disables debug mode
app = create_app(DeploymentConfig)

if __name__ == "__main__":
    """
    Direct execution entry point (not recommended for production).

    This block only runs when the script is executed directly,
    not when imported by a WSGI server.

    For production deployment, use a proper WSGI server like:
    - Gunicorn: gunicorn webServer:app
    - uWSGI: uwsgi --http :5000 --module webServer:app

    Note: Debug mode is enabled here for convenience but should
    be disabled in actual production by using DeploymentConfig's settings.
    """
    # Run the Flask development server
    # Note: debug=True overrides the config setting - remove for production
    app.run(debug=True)