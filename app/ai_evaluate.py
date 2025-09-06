import json
from typing import List

import os, json
import google.generativeai as genai



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

    # Build the complete system rules
    system_rules = (
            "You are a Learning Outcome Evaluation tool for Units in a University "
            "you must follow the following rules and respond with a specific format.\n\n"
            "RULE-- Every Learning Outcome must adhere to Bloom's Taxonomy. The best verbs for each class of Bloom's Taxonomy are as such:\n"
            + BLOOMS_VERBS
            + "RULE-- Units have 6 levels and they should ONLY focus on specific Bloom's classes:\n"
            + LEVEL_RULES
            + "RULE-- Units are also measured by their Credit Points and will have an acceptable range for how many Learning Outcomes there should be:\n"
            + COUNT_RULES
            + "RULE-- The following words and phrases should never be used in Learning Outcomes:\n"
            + BANNED_PHRASES
            + "\n\nSplit with tag 'LO Analysis'\n"
              f"FORMAT-- Check all Learning Outcomes are in the {lo_level} Level.\n\n"
              "FORMAT-- In one sentence per Learning Outcome ending with tag '</LO>':\n"
              "    if the learning outcome is good then say so and move on,\n"
              "    otherwise suggest improvements on the following Learning Outcomes for a\n"
              f"        Level {level} Unit called {unit_name} worth {credit_points} points:\n\n"
              f"{outcomes_block}\n\n"
              "Split with tag 'SUMMARY'\n"
              "FORMAT-- In one or two sentences conclude with an overall evaluation on all Learning Outcomes and if the user is missing any for the unit.\n"
    )

    return system_rules


def run_eval(level, unit_name, credit_points, outcomes_text, config_path: str = "AIConfig.json"):
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
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in configuration file: {config_path}")

    # api_key_text = config["API_key"]
    model_name = config["selected_model"]
    # api_key = api_key_text.strip()
    api_key = os.getenv("GOOGLE_API_KEY") 

    if not api_key:
        return "❌ ERROR: Missing API key. Set GOOGLE_API_KEY in your environment or put it in AIConfig.json."

    try:
        level = int(level)
        credit_points = int(credit_points)
    except Exception:
        return "❌ ERROR: Level and Credit Points must be integers."

    outcomes = outcomes_text.splitlines()
    prompt = build_prompt(level, unit_name, credit_points, outcomes, config)
    # configure SDK once you’ve resolved api_key (you already do above)
    genai.configure(api_key=api_key)

    # use Gemma model from config (or default)
    model = genai.GenerativeModel(model_name)

    try:
        resp = model.generate_content(prompt)   # simple non-streaming call
        return getattr(resp, "text", "") or "⚠️ No text returned."
    except Exception as e:
        return f"❌ ERROR during generation: {e}"

# Example usage:
if __name__ == "__main__":
    # Example call
    outcomes = [
        "create computer algorithms for novel problems",
        "analyse the correctness and complexity of algorithms",
        "implement algorithms in code and test them for correctness and efficiency",
        "evaluate and apply common algorithmic problem-solving techniques",
        "evaluate and apply well-known algorithms"
    ]

    print(run_eval(3, "Advanced Algorithms", 6, "\n".join(outcomes), "AIConfig.json"))