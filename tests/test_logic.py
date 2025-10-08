import pytest
import sys 
import os
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch
from app import create_app
from app import routes
#import project logic functions
from app.routes import (
    getBloomsWordList,
    updateAIParams,
    createCSVofLOs
)

    
#AI Learning Outcome suggestion
def test_getBloomsWordList(monkeypatch):
    """Ensure correct Bloom's verbs are returned for a given level."""
    #Mock configuration structure similar to what config_manager provides
    mock_config = {
        "Level 1": "Knowledge",
        "Level 2": "Comprehension",
        "Level 3": "Application",
        "Level 4": "Analysis",
        "Level 5": "Synthesis",
        "Level 6": "Evaluation",
        "KNOWLEDGE": ["define", "list", "recall"],
        "COMPREHENSION": ["describe", "explain"],
        "APPLICATION": ["apply", "use"],
        "ANALYSIS": ["analyze", "compare"],
        "SYNTHESIS": ["create", "design"],
        "EVALUATION": ["evaluate", "judge"],
    }

    #patch config_manager to return our fake Bloom data
    monkeypatch.setattr(routes.config_manager, "getCurrentParams", lambda: mock_config)

    #test level3
    verbs = routes.getBloomsWordList(3)

    assert isinstance(verbs, list)
    assert "apply" in verbs
    assert "use" in verbs
    assert len(verbs) > 0

    #optional test to mimic old behaviour
    random_verb = random.choice(verbs)
    assert random_verb in mock_config["APPLICATION"]

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