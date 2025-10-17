"""Command handlers for each CLI subcommand."""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from src.cli.utils import (
    filter_questions,
    filter_rules,
    filter_sections,
    load_json_file,
    log_verbose,
    print_summary,
)
from src.lib.openai_client import get_openai_client
from src.pipeline.evaluate import run_evaluation
from src.pipeline.extract import extract_rules
from src.pipeline.generate import generate_questions_for_rule
from src.pipeline.parse import parse_document
from src.pipeline.validate import generate_validation_analysis, validate_and_filter_questions


def cmd_parse(args):
    """Execute 'parse' command - extract sections from PDF.

    Args:
        args: Parsed command-line arguments
    """
    log_verbose(f"Parsing PDF: {args.pdf}")
    if args.section:
        log_verbose(f"Filtering to sections starting with: {args.section}")

    # Parse document
    sections = parse_document(args.pdf, section_prefix=args.section)

    # Save to file
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(sections, f, indent=2, ensure_ascii=False)

    print(f"✓ Extracted {len(sections)} sections")
    print(f"✓ Saved to {args.output}")


def cmd_rules(args):
    """Execute 'rules' command - extract legal rules from sections.

    Args:
        args: Parsed command-line arguments
    """
    log_verbose(f"Loading sections from: {args.input}")

    # Load sections
    sections = load_json_file(args.input)

    # Filter sections if requested
    if args.section:
        log_verbose(f"Filtering to sections starting with: {args.section}")
        sections = filter_sections(sections, args.section)

    if not sections:
        print("No sections found matching filter criteria")
        return

    log_verbose(f"Processing {len(sections)} sections")

    # Get OpenAI client
    client = get_openai_client()

    all_rules = []

    # Extract rules from each section
    for section_id, section_data in sections.items():
        log_verbose(f"Processing section {section_id}...")
        print(f"Processing {section_id}...")
        rules = extract_rules(section_id, section_data, client)
        all_rules.extend(rules)
        log_verbose(f"  Extracted {len(rules)} rules from {section_id}")

    # Save all rules
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_rules, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Extracted {len(all_rules)} total rules")
    print(f"✓ Saved to {args.output}")


def cmd_questions(args):
    """Execute 'questions' command - generate questions from rules.

    Args:
        args: Parsed command-line arguments
    """
    log_verbose(f"Loading rules from: {args.input}")

    # Load rules
    rules = load_json_file(args.input)

    # Filter rules if requested
    if args.rule_id:
        log_verbose(f"Filtering to rules matching: {args.rule_id}")
        rules = filter_rules(rules, args.rule_id)

    if not rules:
        print("No rules found matching filter criteria")
        return

    log_verbose(f"Generating questions for {len(rules)} rules")

    # Parse question types
    if args.types:
        requested_types = [t.strip() for t in args.types.split(",")]
        # Map short names to full type names
        type_map = {
            "def": "definitional",
            "easy": "scenario_easy",
            "hard": "scenario_hard",
            "refusal": "refusal",
        }
        question_types = [type_map.get(t, t) for t in requested_types]
        log_verbose(f"Generating question types: {question_types}")
    else:
        question_types = None  # Generate all types

    # Get OpenAI client
    client = get_openai_client()

    all_questions = []

    # Group rules by section for better organization
    rules_by_section: Dict[str, List[Dict[str, Any]]] = {}
    for rule in rules:
        section_id = rule["source_section"]
        if section_id not in rules_by_section:
            rules_by_section[section_id] = []
        rules_by_section[section_id].append(rule)

    # Generate questions for each section's rules
    for section_id, section_rules in rules_by_section.items():
        print(f"\nProcessing {section_id}: {len(section_rules)} rules")

        for rule_index, rule in enumerate(section_rules):
            rule_id = rule.get("rule_id", f"{section_id}_r{rule_index}")
            log_verbose(f"  Rule {rule_id}: {rule['rule_type']}")
            print(f"  Rule {rule_index + 1}/{len(section_rules)}: {rule['rule_type']}")

            questions = generate_questions_for_rule(
                rule, section_id, rule_index, client, question_types_filter=question_types
            )
            all_questions.extend(questions)

    # Save all questions
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)

    # Print summary
    type_counts = Counter(q["question_type"] for q in all_questions)
    print(f"\n✓ Generated {len(all_questions)} total questions")
    print(f"✓ Saved to {args.output}")
    print("\nQuestion breakdown:")
    for qtype, count in sorted(type_counts.items()):
        print(f"  - {qtype}: {count}")


def cmd_validate(args):
    """Execute 'validate' command - validate generated questions.

    Args:
        args: Parsed command-line arguments
    """
    log_verbose(f"Loading questions from: {args.input}")

    # Load questions
    questions = load_json_file(args.input)

    # Filter questions if requested
    if args.question_id:
        log_verbose(f"Filtering to questions matching: {args.question_id}")
        questions = filter_questions(questions, args.question_id)

    if not questions:
        print("No questions found matching filter criteria")
        return

    log_verbose(f"Validating {len(questions)} questions (threshold: {args.threshold})")

    # Load parsed sections for structural validation
    # Try multiple locations
    sections_paths = ["data/extracted/sections.json", "data/extracted/section_5_5.json"]
    parsed_sections = None
    for path in sections_paths:
        try:
            parsed_sections = load_json_file(path)
            log_verbose(f"Loaded sections from {path}")
            break
        except FileNotFoundError:
            continue

    if parsed_sections is None:
        print("Warning: Could not find parsed sections file")
        print("Tried:", ", ".join(sections_paths))
        print("Structural validation will be limited")
        parsed_sections = {}

    # Load rules for validation
    try:
        rules = load_json_file("data/extracted/rules.json")
    except FileNotFoundError:
        print("Warning: Could not find rules.json")
        print("Validation may be limited")
        rules = []

    # Get OpenAI client
    client = get_openai_client()

    # Validate and filter
    # Note: threshold is currently hardcoded to 90 in validation logic
    # The --threshold argument is available for future use
    print("Applying quality threshold: All components ≥90%")
    validated_questions, rejected_questions, validation_report = validate_and_filter_questions(
        questions, parsed_sections, rules, client=client
    )

    # Save validated questions
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(validated_questions, f, indent=2, ensure_ascii=False)

    # Save rejected questions with reasons
    rejected_output = Path(args.output).parent / "questions_rejected.json"
    with open(rejected_output, "w", encoding="utf-8") as f:
        json.dump(rejected_questions, f, indent=2, ensure_ascii=False)

    # Save validation report
    report_output = Path(args.output).parent / "validation_report.json"
    with open(report_output, "w", encoding="utf-8") as f:
        json.dump(validation_report, f, indent=2, ensure_ascii=False)

    # Generate and save analysis report
    analysis_report = generate_validation_analysis(
        questions, validated_questions, rejected_questions, validation_report, rules
    )
    analysis_output = Path(args.output).parent / "validation_analysis.txt"
    with open(analysis_output, "w", encoding="utf-8") as f:
        f.write(analysis_report)

    # Export to CSV
    from src.pipeline.export import export_to_csv

    csv_output = Path(args.output).parent / "benchmark_questions.csv"
    export_to_csv(validated_questions, str(csv_output))

    # Print results
    print_summary(
        "VALIDATION RESULTS",
        {
            "Total questions": validation_report["total_questions"],
            "Validated": validation_report["validated"],
            "Rejected": validation_report["rejected"],
            "Structural failures": validation_report["structural_failures"],
            "Quality failures": validation_report["quality_failures"],
        },
    )

    print(f"\n✓ Saved validated questions to {args.output}")
    print(f"✓ Saved rejected questions to {rejected_output}")
    print(f"✓ Saved report to {report_output}")
    print(f"✓ Saved analysis to {analysis_output}")
    print(f"✓ Exported to CSV: {csv_output}")

    print("\nValidation breakdown by type:")
    for qtype, counts in sorted(validation_report["by_type"].items()):
        print(f"  - {qtype}: {counts['validated']} validated, {counts['rejected']} rejected")

    # Show sample rejected questions if any
    if rejected_questions:
        print("\nSample rejected question:")
        sample = rejected_questions[0]
        print(f"  ID: {sample['question_id']}")
        print(f"  Type: {sample['question_type']}")
        print(f"  Rejection reason: {sample['_validation'].get('rejected_reason')}")

        # Show structural issues if present
        if "structural_issues" in sample["_validation"]:
            issues = sample["_validation"]["structural_issues"]
            if issues:
                print(f"  Structural issues ({len(issues)}):")
                for issue in issues:
                    print(f"    - {issue}")

        # Show quality failures if present
        if "failures" in sample["_validation"].get("scoring_breakdown", {}):
            failures = sample["_validation"]["scoring_breakdown"]["failures"]
            if failures:
                print(f"  Failed components ({len(failures)}):")
                for comp, score in failures.items():
                    print(f"    - {comp}: {score:.1f} (< 90)")


def cmd_eval(args):
    """Execute 'eval' command - evaluate target model on questions.

    Args:
        args: Parsed command-line arguments
    """
    log_verbose(f"Loading questions from: {args.input}")
    log_verbose(f"Target model: {args.model}")

    # Check if input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}")
        print("Run 'validate' command first to generate validated questions")
        return

    # Get OpenAI client
    client = get_openai_client()

    # Run evaluation
    run_evaluation(
        questions_path=args.input,
        output_path=args.output,
        model=args.model,
        question_filter=args.question_id,
        client=client,
    )

    print("\n✓ Evaluation complete")
    print(f"✓ Results saved to {args.output}")


def cmd_score(args):
    """Execute 'score' command - score evaluation responses.

    Args:
        args: Parsed command-line arguments
    """
    from src.pipeline.score import (
        analyze_confusion,
        generate_analysis_report,
        save_scored_results,
        score_evaluation,
    )

    log_verbose(f"Loading evaluation responses from: {args.input}")

    # Check if input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}")
        print("Run 'eval' command first to generate evaluation responses")
        return

    # Load evaluation responses
    with open(args.input, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    print(f"Scoring {len(eval_data)} responses...")

    # Score responses
    scoring_output = score_evaluation(eval_data)

    # Analyze confusion (MC questions only)
    mc_results = [r for r in scoring_output["scored_results"] if r["question_type"] != "refusal"]
    confusion = analyze_confusion(mc_results)

    # Generate report
    report_text = generate_analysis_report(scoring_output["summary"], confusion)

    # Print report to console
    print("\n" + report_text)

    # Save scored results
    save_scored_results(scoring_output, args.output)
    print(f"Scored results saved to: {args.output}")

    # Save report
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"Analysis report saved to: {args.report}")


def cmd_all(args):
    """Execute 'all' command - run full pipeline.

    Args:
        args: Parsed command-line arguments
    """
    log_verbose("Running full pipeline")

    output_dir = Path(args.output_dir)

    # Phase 1: Parse PDF
    parse_output = output_dir / "extracted" / "sections.json"
    if args.resume and parse_output.exists():
        print("Skipping parse (output exists, --resume enabled)")
    else:
        print("\n" + "=" * 60)
        print("Phase 1: Parse PDF")
        print("=" * 60)
        # Create a namespace for parse command
        parse_args = type(
            "obj",
            (object,),
            {"pdf": args.pdf, "section": args.section, "output": str(parse_output)},
        )()
        cmd_parse(parse_args)

    # Phase 2: Extract rules
    rules_output = output_dir / "extracted" / "rules.json"
    if args.resume and rules_output.exists():
        print("\nSkipping rules extraction (output exists, --resume enabled)")
    else:
        print("\n" + "=" * 60)
        print("Phase 2: Extract Rules")
        print("=" * 60)
        rules_args = type(
            "obj",
            (object,),
            {"input": str(parse_output), "section": args.section, "output": str(rules_output)},
        )()
        cmd_rules(rules_args)

    # Phase 3: Generate questions
    questions_output = output_dir / "generated" / "questions.json"
    if args.resume and questions_output.exists():
        print("\nSkipping question generation (output exists, --resume enabled)")
    else:
        print("\n" + "=" * 60)
        print("Phase 3: Generate Questions")
        print("=" * 60)
        questions_args = type(
            "obj",
            (object,),
            {
                "input": str(rules_output),
                "rule_id": None,
                "types": None,
                "output": str(questions_output),
            },
        )()
        cmd_questions(questions_args)

    # Phase 4: Validate
    validated_output = output_dir / "validated" / "questions.json"
    if args.resume and validated_output.exists():
        print("\nSkipping validation (output exists, --resume enabled)")
    else:
        print("\n" + "=" * 60)
        print("Phase 4: Validate Questions")
        print("=" * 60)
        validate_args = type(
            "obj",
            (object,),
            {
                "input": str(questions_output),
                "question_id": None,
                "threshold": 90,
                "output": str(validated_output),
            },
        )()
        cmd_validate(validate_args)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Final output: {validated_output}")
