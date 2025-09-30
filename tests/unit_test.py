import pytest
import random
from unittest.mock import MagicMock, patch
import sys 
import os
import google.genai as genai
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

#lmport logic functions
from app import create_app

from app.routes import (
    listToStringByComma,
    intListToStringByDash,
    intStringToListByDash,
    returnLOOpener,
    updateAIParams,
    createCSVofLOs
)

# 1. List and string helpers
def test_listToStringByComma():
    assert listToStringByComma(["a", "b"]) == "a, b"
    assert listToStringByComma(["x"]) == "x"
    assert listToStringByComma([]) == ""

def test_intListToStringByDash():
    assert intListToStringByDash([1,2,3]) == "1-2-3"
    assert intListToStringByDash([42]) == "42"
    assert intListToStringByDash([]) == ""

def test_intStringToListByDash():
    assert intStringToListByDash("1-2-3") == [1,2,3]
    assert intStringToListByDash("42") == [42]
    with pytest.raises(ValueError):
        intStringToListByDash("")  # empty string should error

# 2. returnLOOpener
def test_returnLOOpener():
    fake_config = {
        "Level 1": "Knowledge",
        "KNOWLEDGE": ["define", "list"]
    }
    #patch random.choice to make test deterministic
    with patch("random.choice", lambda lst: lst[0]):
        result = returnLOOpener(1)
        print(result)

# 3. updateAIParams
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

# 4. createCSVofLOs
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
