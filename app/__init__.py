from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from .config import DevelopmentConfig
import os
from .ai_handler import ConfigManager

#some init
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login_page'
config_manager = ConfigManager('app/AIConfig.json')


@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))

def create_app(config=DevelopmentConfig):
    flaskApp = Flask(__name__)
    flaskApp.config.from_object(config)
    db.init_app(flaskApp)  
    migrate.init_app(flaskApp, db, render_as_batch=True)
    login_manager.init_app(flaskApp)

    #use blueprints, we probably only need these two since its a fairly small application
    from .routes import main
    from .auth import auth
    flaskApp.register_blueprint(main)
    flaskApp.register_blueprint(auth)

    #app.db can get corrupted in git merges so leaving it in gitignore, this code will check if app.db exists and if not then create it
    appdbPath = os.path.join(os.path.abspath(os.path.dirname(__file__)) , 'app.db')
    if os.path.exists(appdbPath) == False:
         with flaskApp.app_context():
            db.create_all()
            db.session.commit()
            
    @flaskApp.after_request
    def add_header(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

            

    return flaskApp


