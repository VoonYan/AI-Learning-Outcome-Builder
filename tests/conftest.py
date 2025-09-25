import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 

from app import create_app, db as _db
from config import TestingConfig  # You must create this config if it doesn’t exist yet

@pytest.fixture(scope='session')
def app():
    app = create_app(config_class=TestingConfig)

    # Set up the app context
    with app.app_context():
        yield app

@pytest.fixture(scope='session')
def db(app):
    _db.app = app
    _db.create_all()
    yield _db
    _db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
