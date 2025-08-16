from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(config):
    flaskApp = Flask(__name__)
    flaskApp.config.from_object(config)

    from app.blueprints import main
    flaskApp.register_blueprint(main)
    return flaskApp
