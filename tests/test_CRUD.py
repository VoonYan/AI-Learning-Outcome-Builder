import os
import sys
import json
import pytest 
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) 

from app.models import Unit, LearningOutcome, UserType

#create a helper in the test database which has admin permissions 
def admin(db, create_user):
  return create_user(role=UserType.ADMIN)

#login as test client to start testing 
@pytest.fixture 
def client_logged_in(client, admin_user, login_user):
  login_user(admin_user)
  return client 

#to test adding a unit into databse 
@pytest.fixture
def test_unit(db, admin_user):
  unit = Unit(
    unitcode="CS123", unitname="Intro to Life",
    level=1, creditpoints=6,
    description="Navigating life as a student", creatorid=admin_user.id
  )
  db.session.add(unit)
  db.session.commit()
  return unit 

@pytest.fixture 
def test_lo(db, test_unit):
  lo = LearningOutcome(
    unit_id=test_unit.id,
    position=1,
    description="understand algorithms",
    assessment="Exam, Project"
    )
  db.session.add(lo)
  db.session.commit()
  return lo

#UNIT CRUD 
def test_create_unit(client_logged_in, db):
  resp = client_logged_in.post("/new_unit", data={
    "unitcode": "CITS2002",
    "unitname": "Data Structures",
    "level": "2",
    "creditpoints": "6",
    "description":"Learn about data structures"
    }, follow_redirects=True )
  
  assert resp.status_code == 200
  assert b"New Unit" in resp.data
  unit = Unit.query.filter_by(unitcode="CITS2002").first()
  assert unit is not None 
  assert unit.unitname == "Data Structures"
