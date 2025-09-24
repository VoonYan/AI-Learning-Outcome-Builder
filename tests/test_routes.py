import pytest
from app import create_app 

@pytest.fixture
#this creates flask test app
def client():
  app = create_app()
  app.config['TESTING'] = True
  with app.test_client() as client:
    yield client

