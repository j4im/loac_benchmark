"""Test script to run Phase 4 validation on existing questions."""

import json
from pathlib import Path
from src.pipeline.validate import validate_and_filter_questions
from src.lib.openai_client import get_openai_client

# Load generated questions
with open('data/generated/questions.json', 'r', encoding='utf-8') as f:
    questions = json.load(f)

# Load parsed sections
with open('data/extracted/section_5_5.json', 'r', encoding='utf-8') as f:
    parsed_sections = json.load(f)

# Load rules
with open('data/extracted/rules.json', 'r', encoding='utf-8') as f:
    rules = json.load(f)

print(f"Loaded {len(questions)} questions")
print(f"Loaded {len(rules)} rules")
print(f"Loaded {len(parsed_sections)} sections")

# Run validation
client = get_openai_client()

print("\nRunning Phase 4 validation with new threshold-based logic...")
print("Thresholds: Individual components ≥90%, Mean ≥95%\n")

validated, rejected, report = validate_and_filter_questions(
    questions,
    parsed_sections,
    rules,
    client=client
)

# Print results
print(f"\n{'='*60}")
print(f"VALIDATION RESULTS")
print(f"{'='*60}")
print(f"Total questions: {report['total_questions']}")
print(f"Validated: {report['validated']}")
print(f"Rejected: {report['rejected']}")
print(f"Structural failures: {report['structural_failures']}")
print(f"Quality failures: {report['quality_failures']}")
print(f"Average mean score: {report.get('avg_mean_score', 0):.1f}")
print(f"\nValidation method: {report['validation_method']}")
print(f"Thresholds: {report['thresholds']}")

print(f"\nBreakdown by type:")
for qtype, counts in sorted(report['by_type'].items()):
    print(f"  {qtype}: {counts['validated']} validated, {counts['rejected']} rejected")

# Save results
validated_output = Path("data/validated/questions.json")
validated_output.parent.mkdir(parents=True, exist_ok=True)
with open(validated_output, 'w', encoding='utf-8') as f:
    json.dump(validated, f, indent=2, ensure_ascii=False)

rejected_output = Path("data/validated/questions_rejected.json")
with open(rejected_output, 'w', encoding='utf-8') as f:
    json.dump(rejected, f, indent=2, ensure_ascii=False)

report_output = Path("data/validated/validation_report.json")
with open(report_output, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"\n✓ Saved validated questions to {validated_output}")
print(f"✓ Saved rejected questions to {rejected_output}")
print(f"✓ Saved report to {report_output}")

# Show sample rejected questions if any
if rejected:
    print(f"\nSample rejected question:")
    sample = rejected[0]
    print(f"  ID: {sample['question_id']}")
    print(f"  Type: {sample['question_type']}")
    print(f"  Rejection reason: {sample['_validation'].get('rejected_reason')}")
    if 'mean_score' in sample['_validation']:
        print(f"  Mean score: {sample['_validation']['mean_score']:.1f}")
    if 'failures' in sample['_validation'].get('scoring_breakdown', {}):
        failures = sample['_validation']['scoring_breakdown']['failures']
        if failures:
            print(f"  Failed components: {list(failures.keys())}")
