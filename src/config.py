"""Configuration for prompts and constants."""

import re

# Patterns for parsing
SECTION_PATTERN = re.compile(r'^(\d+\.\d+(?:\.\d+)*)\s+(.+)$', re.MULTILINE)
FOOTNOTE_MARKER_PATTERN = re.compile(r'(\d{1,3})')

# Rule extraction prompt for GPT-4.1
RULE_EXTRACTION_PROMPT = """You are a legal analyst extracting rules from the DoD Law of War Manual.

Analyze the following section text and extract ALL distinct legal rules, principles, or definitions.

A "rule" is any statement that:
- Creates an obligation (must, shall, required to)
- Grants permission (may, can, are permitted to)
- States a prohibition (may not, shall not, prohibited)
- Defines a legal term, status, or classification
- Establishes conditions or exceptions

For each rule, provide:
1. rule_text: VERBATIM quote from the source text (do NOT paraphrase or summarize - copy the exact text)
2. rule_type: One of [prohibition, obligation, permission, definition, exception]
3. summary: One-sentence plain language summary
4. actors: Who the rule applies to (e.g., ["combatants"], ["civilians"])
5. conditions: When/where the rule applies (e.g., "during attacks", "in armed conflict")
6. confidence: 0-100 score for how clearly this is a distinct rule
7. footnote_refs: List of footnote numbers mentioned (e.g., [160, 161])

CRITICAL: rule_text MUST be an exact, verbatim quote from the Section Text below. Do NOT paraphrase, summarize, or rewrite.

Section ID: {section_id}
Section Title: {section_title}
Section Text:
{section_text}

Return ONLY a JSON object with a "rules" array. Example:
{{
  "rules": [
    {{
      "rule_text": "Combatants may make enemy combatants the object of attack.",
      "rule_type": "permission",
      "summary": "Combatants can target enemy combatants.",
      "actors": ["combatants"],
      "conditions": "during armed conflict",
      "confidence": 95,
      "footnote_refs": [160]
    }}
  ]
}}
"""
