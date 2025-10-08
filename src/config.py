"""Configuration for prompts and constants."""

import re

# Patterns for parsing
SECTION_PATTERN = re.compile(r'^(\d+\.\d+(?:\.\d+)*)\s+(.+)$', re.MULTILINE)
FOOTNOTE_MARKER_PATTERN = re.compile(r'(\d{1,3})')

# Prompts will be added in Phase 2
RULE_EXTRACTION_PROMPT = """
You are a legal expert analyzing the DoD Law of War Manual. Extract all legal rules from this section.

A "rule" is any statement that:
- Creates an obligation (must, shall, required to)
- Grants permission (may, can, are permitted to)
- States a prohibition (may not, shall not, prohibited)
- Defines a legal status or classification
- Establishes conditions or exceptions

Section {section_id}: {section_title}
Text: {section_text}

For each rule, provide:
1. rule_text: Exact sentence(s) containing the rule
2. rule_type: obligation|permission|prohibition|definition|exception
3. summary: Brief plain-English summary
4. actors: Who the rule applies to
5. conditions: When/how the rule applies
6. confidence: high|medium|low
7. footnote_refs: List of footnote numbers referenced

Return as JSON array.
"""
