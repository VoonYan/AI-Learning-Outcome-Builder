import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app 

@pytest.fixture
#this creates flask test app
def client():
  app = create_app()
  app.config['TESTING'] = True
  with app.test_client() as client:
    yield client

