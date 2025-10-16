"""Argument parser configuration for LOAC QA Pipeline CLI."""

import argparse
import sys


def create_parser():
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog='run_pipeline',
        description='LOAC QA Pipeline - Generate evaluation questions from legal documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline on section 5.5 (uses default PDF)
  run_pipeline all --section 5.5

  # Parse different PDF
  run_pipeline parse --pdf other_manual.pdf --section 5.5

  # Generate questions for specific rule
  run_pipeline questions --rule-id "5.5_r0"

  # Validate with verbose logging
  run_pipeline -v validate

  # Dry-run to see prompts
  run_pipeline -d questions --rule-id "5.5_r0"
        """
    )

    # Global options (apply to all commands)
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Print all LLM prompts and responses to stdout'
    )
    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        help='Print LLM commands without executing (implies --verbose)'
    )
    parser.add_argument(
        '--clean-cache',
        action='store_true',
        help='Delete cache files for this command, then exit'
    )
    parser.add_argument(
        '--ignore-cache',
        action='store_true',
        help="Don't read or write cache (fresh run, no persistence)"
    )
    parser.add_argument(
        '--config',
        metavar='FILE',
        help='Override default config file path'
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        required=True
    )

    # Command: all
    parser_all = subparsers.add_parser(
        'all',
        help='Run full pipeline (parse → rules → questions → validate)',
        description='Execute all stages in sequence'
    )
    parser_all.add_argument(
        '--pdf',
        default='section_5_5.pdf',
        help='Input PDF file (default: section_5_5.pdf)'
    )
    parser_all.add_argument(
        '--section',
        metavar='PREFIX',
        help='Filter to sections starting with PREFIX (e.g., "5.5")'
    )
    parser_all.add_argument(
        '--output-dir',
        default='data/',
        help='Output directory root (default: data/)'
    )
    parser_all.add_argument(
        '--resume',
        action='store_true',
        help='Skip stages with existing output files'
    )

    # Command: parse
    parser_parse = subparsers.add_parser(
        'parse',
        help='Extract sections from PDF',
        description='Parse PDF and extract hierarchical section structure'
    )
    parser_parse.add_argument(
        '--pdf',
        default='section_5_5.pdf',
        help='Input PDF file (default: section_5_5.pdf)'
    )
    parser_parse.add_argument(
        '--section',
        metavar='PREFIX',
        help='Filter to sections starting with PREFIX'
    )
    parser_parse.add_argument(
        '--output',
        default='data/extracted/sections.json',
        help='Save parsed sections JSON (default: data/extracted/sections.json)'
    )

    # Command: rules
    parser_rules = subparsers.add_parser(
        'rules',
        help='Extract legal rules from sections',
        description='Use GPT-4.1 to extract legal rules from parsed sections'
    )
    parser_rules.add_argument(
        '--input',
        default='data/extracted/sections.json',
        help='Parsed sections JSON (default: data/extracted/sections.json)'
    )
    parser_rules.add_argument(
        '--section',
        metavar='PREFIX',
        help='Filter which sections to process'
    )
    parser_rules.add_argument(
        '--output',
        default='data/extracted/rules.json',
        help='Save rules JSON (default: data/extracted/rules.json)'
    )

    # Command: questions
    parser_questions = subparsers.add_parser(
        'questions',
        help='Generate questions from rules',
        description='Generate evaluation questions (4 types per rule)'
    )
    parser_questions.add_argument(
        '--input',
        default='data/extracted/rules.json',
        help='Rules JSON (default: data/extracted/rules.json)'
    )
    parser_questions.add_argument(
        '--rule-id',
        metavar='PATTERN',
        help='Filter rules by glob pattern (e.g., "5.5_r0", "5.5.2_*")'
    )
    parser_questions.add_argument(
        '--types',
        help='Comma-separated question types: def,easy,hard,refusal (default: all)'
    )
    parser_questions.add_argument(
        '--output',
        default='data/generated/questions.json',
        help='Save questions JSON (default: data/generated/questions.json)'
    )

    # Command: validate
    parser_validate = subparsers.add_parser(
        'validate',
        help='Validate generated questions',
        description='Run quality validation on generated questions'
    )
    parser_validate.add_argument(
        '--input',
        default='data/generated/questions.json',
        help='Questions JSON (default: data/generated/questions.json)'
    )
    parser_validate.add_argument(
        '--question-id',
        metavar='PATTERN',
        help='Filter questions by glob pattern (e.g., "*_refusal")'
    )
    parser_validate.add_argument(
        '--threshold',
        type=int,
        default=90,
        help='Quality threshold 0-100 (default: 90)'
    )
    parser_validate.add_argument(
        '--output',
        default='data/validated/questions.json',
        help='Validated questions JSON (default: data/validated/questions.json)'
    )

    return parser


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: List of arguments to parse (defaults to sys.argv[1:])

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = create_parser()

    # If no arguments provided, show help
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) == 0:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args(argv)
