"""Rule extraction from parsed sections using LLM."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from openai import OpenAI


def extract_rules(
    section_id: str,
    section_data: Dict,
    client: Optional[OpenAI] = None
) -> List[Dict]:
    """
    Extract legal rules from a section using GPT-4.1.

    Args:
        section_id: Section identifier (e.g., "5.5.1")
        section_data: Section dict with title, text, page_numbers
        client: OpenAI client (creates new if None)

    Returns:
        List of rule dicts with extracted information
    """
    from src.config import RULE_EXTRACTION_PROMPT
    from src.openai_client import get_openai_client

    if client is None:
        client = get_openai_client()

    # Check cache first
    cache_path = Path(f"cache/rules/{section_id}.json")
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
            print(f"  [Cached] {len(cached_data)} rules")
            return cached_data

    # Build prompt
    prompt = RULE_EXTRACTION_PROMPT.format(
        section_id=section_id,
        section_title=section_data['title'],
        section_text=section_data['text']
    )

    try:
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": "You are a legal analyst extracting rules from legal documents. Return valid JSON only."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for consistency
            response_format={"type": "json_object"}
        )

        # Parse response
        result = json.loads(response.choices[0].message.content)
        rules = result.get("rules", [])

        # Validate that rules are verbatim
        rules = validate_verbatim_rules(rules, section_data['text'])

        # Add source metadata to each rule
        for rule in rules:
            rule['source_section'] = section_id
            rule['source_page_numbers'] = section_data['page_numbers']

        # Log token usage
        usage = response.usage
        cost = estimate_cost(usage)
        print(f"  Tokens: {usage.total_tokens} (input: {usage.prompt_tokens}, output: {usage.completion_tokens})")
        print(f"  Cost: ${cost:.4f}")
        print(f"  Extracted: {len(rules)} rules")

        # Cache result
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)

        return rules

    except Exception as e:
        print(f"  ERROR extracting rules from {section_id}: {e}")
        print(f"  Continuing with remaining sections...")
        return []  # Return empty list, continue with other sections


def estimate_cost(usage) -> float:
    """
    Estimate cost based on token usage.

    GPT-4.1 pricing (gpt-4-turbo):
    - Input: $10.00 per 1M tokens
    - Output: $30.00 per 1M tokens
    """
    input_cost = (usage.prompt_tokens / 1_000_000) * 10.00
    output_cost = (usage.completion_tokens / 1_000_000) * 30.00
    return input_cost + output_cost


def validate_verbatim_rules(rules: List[Dict], source_text: str) -> List[Dict]:
    """
    Validate that rule_text fields are verbatim quotes from source.

    Args:
        rules: List of extracted rules
        source_text: Original section text

    Returns:
        List of rules with validation warnings added where appropriate
    """
    validated_rules = []

    for rule in rules:
        rule_text = rule.get('rule_text', '')

        # Check if rule_text appears verbatim in source
        # Allow for minor whitespace differences
        normalized_source = ' '.join(source_text.split())
        normalized_rule = ' '.join(rule_text.split())

        if normalized_rule not in normalized_source:
            # Flag as non-verbatim
            print(f"  WARNING: Non-verbatim rule detected: {rule_text[:50]}...")
            rule['_validation_warning'] = 'rule_text not found verbatim in source'

        validated_rules.append(rule)

    return validated_rules
