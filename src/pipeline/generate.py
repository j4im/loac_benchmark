"""Question generation from extracted rules using LLM."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI

from src.cli.utils import load_section_text


def generate_definitional(
    rule: Dict, section_id: str, rule_index: int, client: Optional[OpenAI] = None
) -> Dict:
    """
    Generate a definitional multiple-choice question for a rule.

    Args:
        rule: Rule dict with rule_text, rule_type, etc.
        section_id: Section ID (e.g., "5.5.3")
        rule_index: Rule index within section (for question_id)
        client: OpenAI client (creates new if None)

    Returns:
        Question dict with full metadata
    """
    from src.config import DEFINITIONAL_PROMPT
    from src.lib.openai_client import get_openai_client

    if client is None:
        client = get_openai_client()

    # Load section text for context
    section_text = load_section_text(section_id)

    # Build prompt
    prompt = DEFINITIONAL_PROMPT.format(
        rule_text=rule["rule_text"],
        rule_type=rule["rule_type"],
        section_id=section_id,
        section_text=section_text,
    )

    # Call API
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": "You are a legal education expert creating evaluation questions. Return valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,  # Low for definitional questions
        response_format={"type": "json_object"},
    )

    # Parse response
    from src.pipeline.util import parse_llm_json_response

    result = parse_llm_json_response(response)

    # Add metadata
    question = {
        "question_id": f"{section_id}_r{rule_index}_def",
        "question_type": "definitional",
        **result,
        "metadata": {
            "source_section": section_id,
            "source_rule": rule["rule_text"],
            "rule_type": rule["rule_type"],
            "footnotes_used": rule.get("footnote_refs", []),
            "generation_model": "gpt-4.1",
            "generation_timestamp": datetime.utcnow().isoformat(),
            "source_page_numbers": rule.get("source_page_numbers", []),
        },
    }

    return question


def generate_scenario(
    rule: Dict, section_id: str, rule_index: int, difficulty: str, client: Optional[OpenAI] = None
) -> Dict:
    """
    Generate a scenario-based multiple-choice question for a rule.

    Args:
        rule: Rule dict with rule_text, rule_type, etc.
        section_id: Section ID (e.g., "5.5.3")
        rule_index: Rule index within section (for question_id)
        difficulty: "easy" or "hard"
        client: OpenAI client (creates new if None)

    Returns:
        Question dict with full metadata
    """
    from src.config import EASY_SCENARIO_GUIDANCE, HARD_SCENARIO_GUIDANCE, SCENARIO_PROMPT
    from src.lib.openai_client import get_openai_client

    if client is None:
        client = get_openai_client()

    # Select guidance based on difficulty
    guidance = EASY_SCENARIO_GUIDANCE if difficulty == "easy" else HARD_SCENARIO_GUIDANCE

    # Load section text for context
    section_text = load_section_text(section_id)

    # Build prompt
    prompt = SCENARIO_PROMPT.format(
        difficulty=difficulty,
        rule_text=rule["rule_text"],
        rule_type=rule["rule_type"],
        section_id=section_id,
        section_text=section_text,
        difficulty_guidance=guidance,
    )

    # Call API
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": "You are a legal education expert creating evaluation questions. Return valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,  # Moderate for scenario creativity
        response_format={"type": "json_object"},
    )

    # Parse response
    from src.pipeline.util import parse_llm_json_response

    result = parse_llm_json_response(response)

    # Add metadata
    question = {
        "question_id": f"{section_id}_r{rule_index}_scenario_{difficulty}",
        "question_type": f"scenario_{difficulty}",
        **result,
        "metadata": {
            "source_section": section_id,
            "source_rule": rule["rule_text"],
            "rule_type": rule["rule_type"],
            "footnotes_used": rule.get("footnote_refs", []),
            "generation_model": "gpt-4.1",
            "generation_timestamp": datetime.utcnow().isoformat(),
            "source_page_numbers": rule.get("source_page_numbers", []),
        },
    }

    return question


def generate_refusal(
    rule: Dict, section_id: str, rule_index: int, client: Optional[OpenAI] = None
) -> Dict:
    """
    Generate a refusal test question for a rule.

    Args:
        rule: Rule dict with rule_text, rule_type, etc.
        section_id: Section ID (e.g., "5.5.3")
        rule_index: Rule index within section (for question_id)
        client: OpenAI client (creates new if None)

    Returns:
        Question dict with full metadata
    """
    from src.config import REFUSAL_PROMPT
    from src.lib.openai_client import get_openai_client

    if client is None:
        client = get_openai_client()

    # Load section text for context
    section_text = load_section_text(section_id)

    # Build prompt
    prompt = REFUSAL_PROMPT.format(
        rule_text=rule["rule_text"],
        rule_type=rule["rule_type"],
        section_id=section_id,
        section_text=section_text,
    )

    # Call API
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": "You are a red team expert creating refusal test cases. Return valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,  # Moderate creativity for refusal questions
        response_format={"type": "json_object"},
    )

    # Parse response
    from src.pipeline.util import parse_llm_json_response

    result = parse_llm_json_response(response)

    # Add metadata
    question = {
        "question_id": f"{section_id}_r{rule_index}_refusal",
        "question_type": "refusal",
        **result,
        "metadata": {
            "source_section": section_id,
            "source_rule": rule["rule_text"],
            "rule_type": rule["rule_type"],
            "footnotes_used": rule.get("footnote_refs", []),
            "generation_model": "gpt-4.1",
            "generation_timestamp": datetime.utcnow().isoformat(),
            "source_page_numbers": rule.get("source_page_numbers", []),
        },
    }

    return question


def should_generate_refusal(rule: Dict) -> bool:
    """
    Determine if a refusal question should be generated for this rule.

    Per user guidance: Generate refusal questions for ALL rules.
    We'll filter low-confidence questions later in Phase 4.

    Args:
        rule: Rule dict

    Returns:
        Always True (generate for all rules)
    """
    return True


def generate_questions_for_rule(
    rule: Dict,
    section_id: str,
    rule_index: int,
    client: Optional[OpenAI] = None,
    question_types_filter: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Generate all questions (definitional, scenario-easy, scenario-hard, refusal) for a rule.

    Args:
        rule: Rule dict from Phase 2
        section_id: Section ID (e.g., "5.5.3")
        rule_index: Index of rule within section
        client: OpenAI client (creates new if None)
        question_types_filter: Optional list of question types to generate
                              (e.g., ['definitional', 'scenario_easy'])
                              If None, generates all types

    Returns:
        List of question dicts (3-4 questions per rule, or fewer if filtered)
    """
    from src.lib.openai_client import get_openai_client

    if client is None:
        client = get_openai_client()

    # Check cache first (only if no filter, since filtering changes output)
    from src.cli.utils import should_use_cache

    cache_path = Path(f"cache/questions/{section_id}_r{rule_index}.json")
    if should_use_cache() and cache_path.exists() and question_types_filter is None:
        with open(cache_path, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
            print(f"  [Cached] {len(cached_data)} questions")
            return cached_data

    try:
        questions = []

        # Generate definitional question if requested
        if question_types_filter is None or "definitional" in question_types_filter:
            print("  Generating definitional question...")
            questions.append(generate_definitional(rule, section_id, rule_index, client))

        # Generate scenario (easy) if requested
        if question_types_filter is None or "scenario_easy" in question_types_filter:
            print("  Generating scenario (easy) question...")
            questions.append(generate_scenario(rule, section_id, rule_index, "easy", client))

        # Generate scenario (hard) if requested
        if question_types_filter is None or "scenario_hard" in question_types_filter:
            print("  Generating scenario (hard) question...")
            questions.append(generate_scenario(rule, section_id, rule_index, "hard", client))

        # Generate refusal if requested and applicable
        if (
            question_types_filter is None or "refusal" in question_types_filter
        ) and should_generate_refusal(rule):
            print("  Generating refusal question...")
            questions.append(generate_refusal(rule, section_id, rule_index, client))

        # Cache results (unless ignore_cache flag is set)
        if should_use_cache():
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(questions, f, indent=2, ensure_ascii=False)

        print(f"  Generated {len(questions)} questions for rule {rule_index}")

        return questions

    except Exception as e:
        print(f"  ERROR generating questions for rule {rule_index}: {e}")
        print("  Continuing with remaining rules...")
        return []  # Return empty list, continue with other rules
