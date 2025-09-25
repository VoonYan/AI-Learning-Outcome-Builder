import json 
import pytest
from app.models import Unit, LearningOutcome, UserType 

def admin(db, create_user):
  return create_user(role=UserType.ADMIN)

@pytest.fixture 
def client_logged_in(client, admin_user, login_user):
  login_user(admin_user)
  return client 

