#!/usr/bin/env python3
"""
LOAC QA Pipeline - Main orchestration script.

Usage:
    python run_pipeline.py              # Run full pipeline
    python run_pipeline.py --parse-only # Only parse PDF
"""

import argparse
import json
from pathlib import Path
from src.extract import parse_document


def main():
    parser = argparse.ArgumentParser(description="LOAC QA Pipeline")
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Only parse PDF (Phase 1)"
    )
    parser.add_argument(
        "--pdf",
        default="data/raw/section_5_5.pdf",
        help="Path to PDF file"
    )
    parser.add_argument(
        "--output",
        default="data/extracted/section_5_5.json",
        help="Output path for extracted sections"
    )
    parser.add_argument(
        "--section",
        help="Filter to sections starting with this prefix (e.g., '5.5' for 5.5, 5.5.1, 5.5.2, etc.)"
    )

    args = parser.parse_args()

    # Phase 1: Parse PDF
    print(f"Parsing {args.pdf}...")
    if args.section:
        print(f"Filtering to sections starting with {args.section}")
    sections = parse_document(args.pdf, section_prefix=args.section)

    # Save to file
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(sections, f, indent=2, ensure_ascii=False)

    print(f"✓ Extracted {len(sections)} sections")
    print(f"✓ Saved to {args.output}")

    if args.parse_only:
        print("\nDone! (parse-only mode)")
        return

    # Phase 2: Extract rules (coming soon)
    print("\nPhase 2: Rule extraction - Not yet implemented")

    # Phase 3: Generate questions (coming soon)
    print("Phase 3: Question generation - Not yet implemented")

    # Phase 4: Validate (coming soon)
    print("Phase 4: Validation - Not yet implemented")

    # Phase 5: Export (coming soon)
    print("Phase 5: Export - Not yet implemented")


if __name__ == "__main__":
    main()
