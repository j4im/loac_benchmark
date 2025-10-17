"""CLI entry point for LOAC QA Pipeline."""

import sys

import src.cli.utils as cli_utils
from src.cli.commands import (
    cmd_all,
    cmd_eval,
    cmd_parse,
    cmd_questions,
    cmd_rules,
    cmd_score,
    cmd_validate,
)
from src.cli.parser import parse_args
from src.cli.utils import clean_cache_by_command


def main(argv=None):
    """Main CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    try:
        # Parse arguments
        args = parse_args(argv)

        # Set global flags
        cli_utils.VERBOSE_MODE = args.verbose
        cli_utils.DRY_RUN_MODE = args.dry_run
        cli_utils.IGNORE_CACHE = args.ignore_cache

        # Dry-run implies verbose and ignore-cache
        if args.dry_run:
            cli_utils.VERBOSE_MODE = True
            cli_utils.IGNORE_CACHE = True
            print("DRY-RUN MODE: No LLM calls will be made, cache disabled", file=sys.stderr)

        # Handle cache cleaning
        if args.clean_cache:
            clean_cache_by_command(
                args.command,
                section=getattr(args, "section", None),
                rule_id=getattr(args, "rule_id", None),
                question_id=getattr(args, "question_id", None),
            )
            return 0

        # Route to command handler
        command_handlers = {
            "parse": cmd_parse,
            "rules": cmd_rules,
            "questions": cmd_questions,
            "validate": cmd_validate,
            "eval": cmd_eval,
            "score": cmd_score,
            "all": cmd_all,
        }

        handler = command_handlers.get(args.command)
        if handler:
            handler(args)
            return 0
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1

    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if cli_utils.VERBOSE_MODE:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
