import pytest
from app import create_app, db
from app.models import User, UserType, Unit, LearningOutcome
from flask import url_for
import io
import pandas as pd
import sys 
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_bulk_upload(client, login_admin):
    # Create a CSV in memory
    csv_data = """code,title,level,Content,Outcomes
CS103,Algorithms,1,Intro to algorithms,"Understand sorting|*,Understand graphs|*"
CS104,Databases,2,DB concepts,"Learn SQL|*,Learn indexing|*"
"""
    file = (io.BytesIO(csv_data.encode()), "units.csv")

    response = client.post("/import-units", data={
        "import_file": file
    }, content_type="multipart/form-data", follow_redirects=True)

    assert b"units added successfully" in response.data

    # Check database
    unit1 = Unit.query.filter_by(unitcode="CS103").first()
    assert unit1 is not None
    assert len(unit1.learning_outcomes) == 2
    unit2 = Unit.query.filter_by(unitcode="CS104").first()
    assert unit2 is not None
    assert len(unit2.learning_outcomes) == 2