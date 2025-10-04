import pytest
import json
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai_evaluate import build_prompt, run_eval
from app.routes import bloom_guide

# FIXTURE: Sample configuration
@pytest.fixture
def mock_config():
    return {
        "KNOWLEDGE": ["define", "list"],
        "COMPREHENSION": ["explain"],
        "APPLICATION": ["apply"],
        "ANALYSIS": ["analyze"],
        "SYNTHESIS": ["design"],
        "EVALUATION": ["evaluate"],
        "BANNED": ["plagiarize"],
        "Level 1": "knowledge",
        "Level 2": "comprehension",
        "Level 3": "application",
        "Level 4": "analysis",
        "Level 5": "synthesis",
        "Level 6": "evaluation",
        "6 Points": [4, 6],
        "12 Points": [6, 8],
        "24 Points": [8, 12],
        "selected_model": "gemini-pro",
        "API_key": "fake-key"
    }

#test build_prompt()
def test_build_prompt_valid(mock_config):
    outcomes = ["Understand data", "Analyze problems"]
    result = build_prompt(3, "Data Science", 6, outcomes, mock_config)

    assert "Learning Outcome Evaluation tool" in result
    assert "Level 3" in result
    assert "Analyze problems" in result
    assert "KNOWLEDGE:" in result
    assert "SUGGESTION:" in result  # required part of prompt


def test_build_prompt_invalid_level(mock_config):
    """Ensure invalid level raises ValueError."""
    with pytest.raises(ValueError):
        build_prompt(7, "Fake Unit", 6, ["Test outcome"], mock_config)


def test_build_prompt_empty_outcomes(mock_config):
    """Empty or blank outcomes should insert placeholder."""
    result = build_prompt(2, "Intro Unit", 6, [""], mock_config)
    assert "'(no outcomes provided)'" in result


#test run_eval()
def test_run_eval_missing_api_key(monkeypatch, mock_config):
    """Should return error if API key missing."""
    mock_config["API_key"] = ""
    monkeypatch.setattr("app.ai_evaluate.config_manager.getCurrentParams", lambda: mock_config)

    result = run_eval(3, "Data Science", 6, "Analyze data")
    assert "ERROR: Missing API key" in result


def test_run_eval_invalid_level_creditpoints(monkeypatch, mock_config):
    """Should return error if level or credit_points are not integers."""
    monkeypatch.setattr("app.ai_evaluate.config_manager.getCurrentParams", lambda: mock_config)

    result = run_eval("abc", "Unit X", "notnum", "Understand data")
    assert "Level and Credit Points must be integers" in result


def test_run_eval_successful(monkeypatch, mock_config):
    """Should call GenAI client and return generated text."""
    mock_resp = MagicMock(text="Good response")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    # Patch genai.Client to return mock_client
    monkeypatch.setattr("app.ai_evaluate.genai.Client", lambda api_key=None: mock_client)
    monkeypatch.setattr("app.ai_evaluate.config_manager.getCurrentParams", lambda: mock_config)

    result = run_eval(3, "Data Science", 6, "Analyze data")
    assert "Good response" in result


def test_run_eval_handles_api_exception(monkeypatch, mock_config):
    """Should catch exceptions raised by API call."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API Failure")

    monkeypatch.setattr("app.ai_evaluate.genai.Client", lambda api_key=None: mock_client)
    monkeypatch.setattr("app.ai_evaluate.config_manager.getCurrentParams", lambda: mock_config)

    result = run_eval(3, "Unit Y", 6, "Apply knowledge")
    assert "ERROR during generation" in result or "Try again" in result
