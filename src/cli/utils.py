"""Shared utilities for CLI: filtering, logging, dry-run, cache management."""

import fnmatch
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


# Global flags for runtime behavior
VERBOSE_MODE = False
DRY_RUN_MODE = False
IGNORE_CACHE = False


def filter_sections(sections: Dict[str, Any], prefix: Optional[str]) -> Dict[str, Any]:
    """Filter sections by prefix.

    Args:
        sections: Dict of section_id -> section_data
        prefix: Section prefix (e.g., "5.5" matches "5.5", "5.5.1", "5.5.2", etc.)

    Returns:
        Filtered dict of sections
    """
    if not prefix:
        return sections

    filtered = {}
    for section_id, section_data in sections.items():
        if section_id.startswith(prefix):
            filtered[section_id] = section_data

    return filtered


def filter_rules(rules: List[Dict[str, Any]], pattern: Optional[str]) -> List[Dict[str, Any]]:
    """Filter rules by rule_id glob pattern.

    Args:
        rules: List of rule dicts
        pattern: Glob pattern (e.g., "5.5_r0", "5.5.2_*", "*_r0")

    Returns:
        Filtered list of rules
    """
    if not pattern:
        return rules

    filtered = []
    for rule in rules:
        rule_id = rule.get('rule_id', '')
        if fnmatch.fnmatch(rule_id, pattern):
            filtered.append(rule)

    return filtered


def filter_questions(questions: List[Dict[str, Any]], pattern: Optional[str]) -> List[Dict[str, Any]]:
    """Filter questions by question_id glob pattern.

    Args:
        questions: List of question dicts
        pattern: Glob pattern (e.g., "*_refusal", "5.5_r0_*")

    Returns:
        Filtered list of questions
    """
    if not pattern:
        return questions

    filtered = []
    for question in questions:
        question_id = question.get('question_id', '')
        if fnmatch.fnmatch(question_id, pattern):
            filtered.append(question)

    return filtered


def log_verbose(message: str):
    """Print message to stdout if verbose mode is enabled.

    Args:
        message: Message to print
    """
    if VERBOSE_MODE or DRY_RUN_MODE:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}", file=sys.stderr)


def log_llm_call(model: str, prompt: str, response: Optional[str] = None,
                 tokens: Optional[int] = None, cost: Optional[float] = None):
    """Log LLM call details in verbose mode.

    Args:
        model: Model name
        prompt: Prompt text (will be truncated if long)
        response: Response text (optional)
        tokens: Token count (optional)
        cost: Estimated cost in USD (optional)
    """
    if not (VERBOSE_MODE or DRY_RUN_MODE):
        return

    # Truncate prompt for readability
    # prompt_preview = prompt[:500] + ('...' if len(prompt) > 500 else '')
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


def clean_cache_dir(cache_dir: str, pattern: Optional[str] = None):
    """Delete cache files in a directory.

    Args:
        cache_dir: Cache directory path (e.g., "cache/rules")
        pattern: Optional glob pattern for filtering (e.g., "5.5_*")
    """
    cache_path = Path(cache_dir)
    if not cache_path.exists():
        print(f"Cache directory not found: {cache_dir}")
        return

    deleted_count = 0
    if pattern:
        # Filter by pattern
        for cache_file in cache_path.glob('*.json'):
            if fnmatch.fnmatch(cache_file.stem, pattern):
                cache_file.unlink()
                deleted_count += 1
                print(f"Deleted: {cache_file}")
    else:
        # Delete all
        for cache_file in cache_path.glob('*.json'):
            cache_file.unlink()
            deleted_count += 1
            print(f"Deleted: {cache_file}")

    if deleted_count == 0:
        print(f"No cache files found matching criteria in {cache_dir}")
    else:
        print(f"Deleted {deleted_count} cache file(s) from {cache_dir}")


def clean_cache_by_command(command: str, section: Optional[str] = None,
                           rule_id: Optional[str] = None, question_id: Optional[str] = None):
    """Clean cache based on command and filters.

    Args:
        command: Command name (parse, rules, questions, validate, all)
        section: Section filter
        rule_id: Rule ID filter
        question_id: Question ID filter
    """
    print(f"Cleaning cache for command: {command}")

    if command == 'parse' or command == 'all':
        clean_cache_dir('cache/parse')

    if command == 'rules' or command == 'all':
        if section:
            # Filter cache files by section prefix
            clean_cache_dir('cache/rules', pattern=f"{section}*")
        else:
            clean_cache_dir('cache/rules')

    if command == 'questions' or command == 'all':
        if rule_id:
            # Filter cache files by rule_id pattern
            clean_cache_dir('cache/questions', pattern=f"{rule_id}*")
        else:
            clean_cache_dir('cache/questions')

    if command == 'validate' or command == 'all':
        if question_id:
            # Filter cache files by question_id pattern
            clean_cache_dir('cache/validation', pattern=f"{question_id}*")
        else:
            clean_cache_dir('cache/validation')


def should_use_cache() -> bool:
    """Check if caching should be used.

    Returns:
        True if cache should be used, False otherwise
    """
    return not IGNORE_CACHE


def load_json_file(filepath: str) -> Any:
    """Load JSON file with error handling.

    Args:
        filepath: Path to JSON file

    Returns:
        Parsed JSON data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is malformed
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(data: Any, filepath: str):
    """Save data to JSON file.

    Args:
        data: Data to save
        filepath: Output file path
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    log_verbose(f"Saved to {filepath}")


def print_summary(title: str, stats: Dict[str, Any]):
    """Print a formatted summary.

    Args:
        title: Summary title
        stats: Dictionary of statistics to display
    """
    print(f"\n{'=' * 60}")
    print(title.center(60))
    print('=' * 60)
    for key, value in stats.items():
        print(f"{key}: {value}")
    print('=' * 60)


def load_section_text(section_id: str) -> str:
    """Load section text for a given section ID.

    This function searches for parsed sections in known locations
    and returns the text for the specified section.

    Args:
        section_id: Section ID (e.g., "5.5.3")

    Returns:
        Section text, or empty string if not found
    """
    # Try multiple locations for sections file
    sections_paths = [
        'data/extracted/sections.json',
        'data/extracted/section_5_5.json'
    ]

    for path_str in sections_paths:
        path = Path(path_str)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                sections = json.load(f)
                if section_id in sections:
                    return sections[section_id].get('text', '')

    # If not found, return empty string
    return ""
