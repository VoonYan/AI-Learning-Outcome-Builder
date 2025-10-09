import pytest
import sys 
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.routes import listToStringByComma, intListToStringByDash, intStringToListByDash

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
