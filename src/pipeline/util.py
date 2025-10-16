"""Shared utilities for pipeline operations: LLM response parsing, logging."""

import json
import sys
from typing import Optional

# Import global flags from CLI
from src.cli.utils import DRY_RUN_MODE, VERBOSE_MODE


def parse_llm_json_response(response) -> dict:
    """Parse JSON from OpenAI response.

    Args:
        response: OpenAI ChatCompletion response object

    Returns:
        Parsed JSON dict

    Raises:
        json.JSONDecodeError: If response is not valid JSON
    """
    return json.loads(response.choices[0].message.content)


def log_llm_call(
    model: str,
    prompt: str,
    response: Optional[str] = None,
    tokens: Optional[int] = None,
    cost: Optional[float] = None,
):
    """Log LLM call details in verbose mode.

    Args:
        model: Model name
        prompt: Prompt text
        response: Response text (optional)
        tokens: Token count (optional)
        cost: Estimated cost in USD (optional)
    """
    if not (VERBOSE_MODE or DRY_RUN_MODE):
        return

    # Full prompt in verbose mode (no truncation)
    prompt_preview = prompt

    print("=" * 80, file=sys.stderr)
    print(f"LLM CALL: {model}", file=sys.stderr)
    print("-" * 80, file=sys.stderr)
    print("PROMPT:", file=sys.stderr)
    print(prompt_preview, file=sys.stderr)

    if response:
        print("-" * 80, file=sys.stderr)
        print("RESPONSE:", file=sys.stderr)
        print(response, file=sys.stderr)

    if tokens or cost:
        print("-" * 80, file=sys.stderr)
        if tokens:
            print(f"Tokens: {tokens}", file=sys.stderr)
        if cost:
            print(f"Estimated cost: ${cost:.4f}", file=sys.stderr)

    print("=" * 80, file=sys.stderr)
