import pytest
import sys
import os
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.routes import bloom_guide


# Bloom's Taxonomy Display Tests
def test_bloom_guide_renders_correctly(monkeypatch):
    """Test that bloom_guide correctly builds config and passes JSON to template."""

    #to mock configuration data returned by config_manager
    mock_config = {
        "KNOWLEDGE": ["define", "list", "recall"],
        "COMPREHENSION": ["explain", "summarize"],
        "APPLICATION": ["use", "implement"],
        "ANALYSIS": ["compare", "differentiate"],
        "SYNTHESIS": ["design", "construct"],
        "EVALUATION": ["judge", "critique"],
        "BANNED": ["plagiarize", "copy"],
        "Level 1": "knowledge",
        "Level 2": "comprehension",
        "Level 3": "application",
        "Level 4": "analysis",
        "Level 5": "synthesis",
        "Level 6": "evaluation",
        "6 Points": [1, 2],
        "12 Points": [3, 4],
        "24 Points": [5, 6],
    }

    monkeypatch.setattr("app.routes.config_manager.getCurrentParams", lambda: mock_config.copy())

    #patch render_template to capture inputs
    captured = {}
    def mock_render(template, **kwargs):
        captured["template"] = template
        captured["config"] = kwargs["config"]
        captured["config_json"] = json.loads(kwargs["config_json"])
        return "rendered_bloom_page"

    monkeypatch.setattr("app.routes.render_template", mock_render)

    #Call bloom_guide()
    result = bloom_guide()

    #Verify outputs 
    assert result == "rendered_bloom_page"
    assert captured["template"] == "bloom_guide.html"

    #ensure credit point fields were processed into template-friendly form
    assert captured["config"]["6_Points_Min"] == 1
    assert captured["config"]["6_Points_Max"] == 2
    assert captured["config"]["12_Points_Min"] == 3
    assert captured["config"]["12_Points_Max"] == 4
    assert captured["config"]["24_Points_Min"] == 5
    assert captured["config"]["24_Points_Max"] == 6

    #verify config_json contains Bloom levels and point ranges
    cfg_json = captured["config_json"]
    for key in [
        "KNOWLEDGE", "COMPREHENSION", "APPLICATION", "ANALYSIS",
        "SYNTHESIS", "EVALUATION", "BANNED", "Level 1", "Level 6"
    ]:
        assert key in cfg_json

    #verify verbs are lists and contain at least one value
    for verbs in [
        cfg_json["KNOWLEDGE"],
        cfg_json["COMPREHENSION"],
        cfg_json["APPLICATION"],
        cfg_json["ANALYSIS"],
        cfg_json["SYNTHESIS"],
        cfg_json["EVALUATION"]
    ]:
        assert isinstance(verbs, list)
        assert len(verbs) > 0


def test_bloom_guide_handles_missing_keys(monkeypatch):
    """Test bloom_guide gracefully handles missing optional fields."""

    # Mock configuration missing some fields
    partial_config = {
        "KNOWLEDGE": ["define"],
        "COMPREHENSION": ["explain"],
        "APPLICATION": ["use"],
        "ANALYSIS": ["analyze"],
        "SYNTHESIS": ["build"],
        "EVALUATION": ["evaluate"],
        "BANNED": [],
        "Level 1": "knowledge",
        "Level 2": "comprehension",
        "Level 3": "application",
        "Level 4": "analysis",
        "Level 5": "synthesis",
        "Level 6": "evaluation",
        # Missing point ranges → should raise KeyError if not handled
        "6 Points": [0, 0],
        "12 Points": [0, 0],
        "24 Points": [0, 0],
    }

    monkeypatch.setattr("app.routes.config_manager.getCurrentParams", lambda: partial_config.copy())

    monkeypatch.setattr("app.routes.render_template", lambda *a, **k: "rendered_minimal")

    result = bloom_guide()
    assert result == "rendered_minimal"

