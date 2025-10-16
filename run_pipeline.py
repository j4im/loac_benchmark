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
from src.pipeline.parse import parse_document
from src.pipeline.extract import extract_rules
from src.lib.openai_client import get_openai_client


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

    # Phase 2: Extract rules
    print("\nPhase 2: Extracting rules from sections...")
    client = get_openai_client()

    all_rules = []

    for section_id, section_data in sections.items():
        print(f"Processing {section_id}...")
        rules = extract_rules(section_id, section_data, client)
        all_rules.extend(rules)

    # Save all rules
    rules_output = Path(args.output).parent / "rules.json"
    with open(rules_output, 'w', encoding='utf-8') as f:
        json.dump(all_rules, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Extracted {len(all_rules)} total rules")
    print(f"✓ Saved to {rules_output}")

    # Phase 3: Generate questions
    print("\nPhase 3: Generating questions from rules...")
    from src.pipeline.generate import generate_questions_for_rule
    from collections import Counter

    all_questions = []

    # Group rules by section for better organization
    rules_by_section = {}
    for rule in all_rules:
        section_id = rule['source_section']
        if section_id not in rules_by_section:
            rules_by_section[section_id] = []
        rules_by_section[section_id].append(rule)

    # Generate questions for each section's rules
    for section_id, section_rules in rules_by_section.items():
        print(f"\nProcessing {section_id}: {len(section_rules)} rules")

        for rule_index, rule in enumerate(section_rules):
            print(f"  Rule {rule_index + 1}/{len(section_rules)}: {rule['rule_type']}")
            questions = generate_questions_for_rule(rule, section_id, rule_index, client)
            all_questions.extend(questions)

    # Save all questions
    questions_output = Path("data/generated/questions.json")
    questions_output.parent.mkdir(parents=True, exist_ok=True)
    with open(questions_output, 'w', encoding='utf-8') as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Generated {len(all_questions)} total questions")
    print(f"✓ Saved to {questions_output}")

    # Print summary by type
    type_counts = Counter(q['question_type'] for q in all_questions)
    print("\nQuestion breakdown:")
    for qtype, count in sorted(type_counts.items()):
        print(f"  - {qtype}: {count}")

    # Phase 4: Validate
    print("\nPhase 4: Validating question quality...")
    from src.pipeline.validate import validate_and_filter_questions

    # Load parsed sections for structural validation
    with open(args.output, 'r', encoding='utf-8') as f:
        parsed_sections = json.load(f)

    # Validate and filter
    print(f"Applying quality threshold: All components ≥90%")
    validated_questions, rejected_questions, validation_report = validate_and_filter_questions(
        all_questions,
        parsed_sections,
        all_rules,  # From Phase 2
        client=client
    )

    # Save validated questions
    validated_output = Path("data/validated/questions.json")
    validated_output.parent.mkdir(parents=True, exist_ok=True)
    with open(validated_output, 'w', encoding='utf-8') as f:
        json.dump(validated_questions, f, indent=2, ensure_ascii=False)

    # Save rejected questions with reasons
    rejected_output = Path("data/validated/questions_rejected.json")
    with open(rejected_output, 'w', encoding='utf-8') as f:
        json.dump(rejected_questions, f, indent=2, ensure_ascii=False)

    # Save validation report
    report_output = Path("data/validated/validation_report.json")
    with open(report_output, 'w', encoding='utf-8') as f:
        json.dump(validation_report, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Validated {validation_report['validated']}/{validation_report['total_questions']} questions")
    print(f"✓ Structural failures: {validation_report['structural_failures']}")
    print(f"✓ Quality threshold failures: {validation_report['quality_failures']}")
    print(f"✓ Saved to {validated_output}")
    print(f"✓ Rejected {validation_report['rejected']} questions to {rejected_output}")

    print("\nValidation breakdown by type:")
    for qtype, counts in sorted(validation_report['by_type'].items()):
        print(f"  - {qtype}: {counts['validated']} validated, {counts['rejected']} rejected")

    # Phase 5: Export (coming soon)
    print("\nPhase 5: Export - Not yet implemented")


if __name__ == "__main__":
    main()
