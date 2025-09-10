import json
from typing import List
from . import config_manager

import os, json
import google.genai as genai
from google.genai import types


def build_prompt(level: int, unit_name: str, credit_points: int, outcomes: List[str],
                 config) -> str:
    """
    Build a prompt for Learning Outcome evaluation using configuration from JSON file.

    Args:
        level: Unit level (1-6)
        unit_name: Name of the unit
        credit_points: Credit points for the unit
        outcomes: List of learning outcomes to evaluate
        config_path: Config file from runeval

    Returns:
        str: Formatted prompt string
    """

    # Build LEVEL_NAME mapping from config
    LEVEL_NAME = {
        1: config["Level 1"],
        2: config["Level 2"],
        3: config["Level 3"],
        4: config["Level 4"],
        5: config["Level 5"],
        6: config["Level 6"]
    }

    # Validate level
    if level not in LEVEL_NAME:
        raise ValueError("level must be an integer 1–6")

    lo_level = LEVEL_NAME[level]

    # Build Bloom's verbs string from config
    BLOOMS_VERBS = (
        f"KNOWLEDGE: {', '.join(config['KNOWLEDGE'])}.\n"
        f"COMPREHENSION: {', '.join(config['COMPREHENSION'])}.\n"
        f"APPLICATION: {', '.join(config['APPLICATION'])}.\n"
        f"ANALYSIS: {', '.join(config['ANALYSIS'])}.\n"
        f"SYNTHESIS: {', '.join(config['SYNTHESIS'])}.\n"
        f"EVALUATION: {', '.join(config['EVALUATION'])}.\n"
    )

    # Build level rules string from config
    LEVEL_RULES = (
        f"Level 1: {config['Level 1']}.\n"
        f"Level 2: {config['Level 2']}.\n"
        f"Level 3: {config['Level 3']}.\n"
        f"Level 4: {config['Level 4']}.\n"
        f"Level 5: {config['Level 5']}.\n"
        f"Level 6: {config['Level 6']}.\n"
    )

    # Build count rules string from config
    COUNT_RULES = (
        f"6 Points: {config['6 Points'][0]} to {config['6 Points'][1]} Learning Outcomes.\n"
        f"12 Points: {config['12 Points'][0]} to {config['12 Points'][1]} Learning Outcomes.\n"
        f"24 Points: {config['24 Points'][0]} to {config['24 Points'][1]} Learning Outcomes.\n"
    )

    # Build banned phrases string from config
    BANNED_PHRASES = ', '.join(config['BANNED'])

    # Quote outcomes one-per-line
    formatted_outcomes = []
    for o in outcomes:
        o = o.strip()
        if not o:
            continue
        if not (o.startswith("'") and o.endswith("'")):
            o = f"'{o}'"
        formatted_outcomes.append(o)

    outcomes_block = "\n".join(formatted_outcomes) if formatted_outcomes else "'(no outcomes provided)'"

    # Build the complete system rules with structured format
    system_rules = (
            "You are a Learning Outcome Evaluation tool for Units in a University. "
            "You must follow the following rules and respond with a SPECIFIC FORMAT.\n\n"
            "RULE-- Every Learning Outcome must adhere to Bloom's Taxonomy. The best verbs for each class of Bloom's Taxonomy are:\n"
            + BLOOMS_VERBS
            + "RULE-- Units have 6 levels and they should ONLY focus on specific Bloom's classes:\n"
            + LEVEL_RULES
            + "RULE-- Units are also measured by their Credit Points and will have an acceptable range for how many Learning Outcomes there should be:\n"
            + COUNT_RULES
            + "RULE-- The following words and phrases should never be used in Learning Outcomes:\n"
            + BANNED_PHRASES
            + "\n\n**CRITICAL OUTPUT FORMAT INSTRUCTIONS**\n"
              "You MUST structure your response EXACTLY as follows:\n\n"
              "**LO Analysis**\n\n"
              f"Check all Learning Outcomes are appropriate for {lo_level} Level (Level {level}).\n"
              "For EACH learning outcome, write ONE paragraph in this EXACT format:\n"
              "'[outcome text exactly as provided]' - STATUS:[GOOD/NEEDS_REVISION/COULD_IMPROVE] - [Your evaluation in one or two sentences. "
              "If STATUS is NEEDS_REVISION or COULD_IMPROVE, end with: SUGGESTION: '[your specific suggested revision]']\n\n"
              "Status definitions:\n"
              "- Use STATUS:GOOD when the outcome is appropriate for the level and needs no changes\n"
              "- Use STATUS:NEEDS_REVISION when the outcome is at the wrong Bloom's level or has serious issues\n"
              "- Use STATUS:COULD_IMPROVE when the outcome is acceptable but could be strengthened\n\n"
              f"Learning Outcomes to evaluate for Level {level} Unit called {unit_name} worth {credit_points} points:\n\n"
              f"{outcomes_block}\n\n"
              "**SUMMARY**\n\n"
              "In one or two sentences, provide an overall evaluation of all Learning Outcomes, "
              f"noting if the quantity is appropriate for a {credit_points}-point unit "
              f"(should have {config[f'{credit_points} Points'][0]} to {config[f'{credit_points} Points'][1]} outcomes) "
              "and if they align with the expected Bloom's level.\n"
    )

    return system_rules


def run_eval(level, unit_name, credit_points, outcomes_text):
    """
    Run evaluation of learning outcomes using GenAI API.

    Args:
        level: Unit level (1-6)
        unit_name: Name of the unit
        credit_points: Credit points for the unit
        outcomes_text: List of learning outcomes to evaluate
        config_path: Config file

    Returns:
        str: Outcome of evaluation or error message
    """
    # Load configuration from JSON file
    config = config_manager.getCurrentParams()

    model_name = config["selected_model"]
    if config["API_key"] == 'environ':
        api_key = os.getenv("GOOGLE_API_KEY")
    else:
        api_key = config["API_key"]

    if not api_key:
        return "❌ERROR: Missing API key. Set GOOGLE_API_KEY in your environment or put it in AIConfig.json."

    try:
        level = int(level)
        credit_points = int(credit_points)
    except Exception:
        return "❌ERROR: Level and Credit Points must be integers."

    outcomes = outcomes_text.splitlines()
    prompt = build_prompt(level, unit_name, credit_points, outcomes, config)
    # print(prompt)

    # configure SDK
    client = genai.Client(api_key=api_key)

    resp = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0
        )
    )

    try:
        return getattr(resp, "text", "") or "⚠️ No text returned."
    except Exception as e:
        # genai will raise APIException child Exceptions so we can except that specifically
        # but it will also return a large exception object we dont want to print all of it so we should probably do some error checkign here rather than returining just e
        return f"❌ERROR during generation: {e}. Try again in 1 minute."