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

def test_homepage_anonymous(client):
  #to test homepage as guest
  response = client.get('/', follow_redirects=False)
  assert response.status_code == 302
  assert "/home" in response.headers["Location"]
  
def test_homepage_redirect_logged_in(client):
  #to test homepage redirect when logged in
  with client.session_transaction() as sess:
    sess['_user_id'] = 1 
  
  response = client.get('/', follow_redirects=False)
  assert response.status_code == 302
  assert "/main_page" in response.headers["Location"]

def test_help_page(client):
  #to test help page
  response = client.get('/help')
  assert response.status_code == 200
  assert b"Help" in response.data
  
def test_bloom_guide(client):
  #to test bloom guide page
  response = client.get('/bloom-guide')
  assert response.status_code == 200
  assert b"Bloom's Taxonomy" in response.data 
