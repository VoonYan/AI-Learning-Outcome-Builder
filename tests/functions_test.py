import pytest 
import sys
import os 

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.routes import (
    listToStringByComma,
    intListToStringByDash,
    intStringToListByDash,
    returnLOOpener,
    updateAIParams,
    createCSVofLOs
)

#run tests multiple times each with different inputs and expected outputs
@pytest.mark.parametrize("int,expected", [
    (["a","b"],"a,b"),
    (["x"], "x"),
    ([], ""),
    ([" a "], " a "),  # whitespace preserved
    (["hello", "world!"], "hello, world!"),  # special chars
])
def test_list_to_string_by_comma():
    assert listToStringByComma(["a", "b"]) == "a, b"
    assert listToStringByComma(["x"]) == "x"
    assert listToStringByComma([]) == ""

def test_int_list_to_string_by_dash():
    assert intListToStringByDash([1, 2, 3]) == "1-2-3"
    assert intListToStringByDash([42]) == "42"
    assert intListToStringByDash([]) == ""

def test_int_string_to_list_by_dash():
    assert intStringToListByDash("1-2-3") == [1, 2, 3]
    assert intStringToListByDash("42") == [42]
    with pytest.raises(ValueError):
        intStringToListByDash("")  # empty string should error

#logic 
def test_returnLOOpener(monkeypatch):
    fake_config = {
        "Level 1": "Knowledge",
        "Knowledge": ["define", "list"]
    }
    monkeypatch.setattr("app.routes.config_manager.getCurrentParams", lambda: fake_config)

    result = returnLOOpener(1)
    assert result.endswith("... ")
    assert any(word in result for word in fake_config["Knowledge"])

def test_updateAIParams(monkeypatch):
    updated = {}
    monkeypatch.setattr("app.routes.config_manager.replaceCurrentParameter",
                        lambda key, value: updated.setdefault(key, value))

    updateAIParams({
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
    })

    assert updated["selected_model"] == "test-model"
    assert updated["KNOWLEDGE"] == ["define", "list"]
    assert updated["6 Points"] == [1, 2]

#csv
def test_create_csv_of_los(db, test_unit, test_lo):
    csv_data = createCSVofLOs()
    assert "CS123" in csv_data
    assert "understand algorithms" in csv_data
