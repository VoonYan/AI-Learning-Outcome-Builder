import pytest
import sys 
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from app import create_app
#import project logic functions
from app.routes import (
    #returnLOOpener,
    updateAIParams,
    createCSVofLOs
)

@pytest.fixture
def app_context(app):
    """Push app context for tests that require it"""
    yield
    
#AI Learning Outcome suggestion
#def test_returnLOOpener():
    #fake_config = {
        #"Level 1": "Knowledge",
        #"KNOWLEDGE": ["define", "list"]
    #}
    #patch random.choice to make test deterministic
    #with patch("random.choice", lambda lst: lst[0]):
        #result = returnLOOpener(1)
        #print(result)      #proper formatting

#Update AI Parameters
def test_updateAIParams():
    updated = {}
    
    # patch config_manager.replaceCurrentParameter
    with patch("app.routes.config_manager.replaceCurrentParameter", lambda key, value: updated.setdefault(key, value)):
        data = {
            "model": "test-model",
            "apikey": "secret",
            "knowledge": "define, list",
            "comprehension": "explain",
            "application": "apply",
            "analysis": "analyze",
            "synthesis": "combine",
            "evaluation": "judge",
            "banned": "bad",
            "level1": "Knowledge",
            "level2": "Comprehension",
            "level3": "Application",
            "level4": "Analysis",
            "level5": "Synthesis",
            "level6": "Evaluation",
            "cp6": "1-2",
            "cp12": "3-4",
            "cp24": "5-6",
        }
        updateAIParams(data)
        assert updated["selected_model"] == "test-model"
        assert updated["KNOWLEDGE"] == ["define", "list"]
        assert updated["6 Points"] == [1,2]

#CSV Export logic 
def test_createCSVofLOs():
    app = create_app()
    with app.app_context():
        # Mock Unit and LearningOutcome
        class MockLO:
            def __init__(self, description, assessment):
                self.description = description
                self.assessment = assessment

        class MockUnit:
            def __init__(self, unitcode, unitname, level, creditpoints, description, los):
                self.id =id
                self.unitcode = unitcode
                self.unitname = unitname
                self.level = level
                self.creditpoints = creditpoints
                self.description = description
                self.learning_outcomes = los

        los = [MockLO("outcome1", "A"), MockLO("outcome2", "B")]
        unit = MockUnit("CS101", "Intro", 1, 6, "Desc", los)

        with patch("app.routes.Unit.query") as mock_query:
            mock_query.all.return_value = [unit]
            csv_data = createCSVofLOs()
            assert "CS101" in csv_data
            assert "outcome1" in csv_data
            assert "outcome2" in csv_data