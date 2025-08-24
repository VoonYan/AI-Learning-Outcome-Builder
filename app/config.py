import os
basedir = os.path.abspath(os.path.dirname(__file__))
class Config:
    SECRET_KEY = os.environ.get('AI_BUILDER_KEY', 'default_secret_key')

class DeploymentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')

class TestingConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///memory'
    TESTING = True

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True