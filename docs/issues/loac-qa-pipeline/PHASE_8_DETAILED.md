# Phase 8: Export & Format Conversion

**Status**: ✅ COMPLETE
**Started**: 2025-10-16
**Completed**: 2025-10-16
**Objective**: Automatically export validated questions to standardized CSV format during validation

## Overview

Integrate CSV export as a side effect of the validation process. When `validate` command completes, it automatically generates:
1. JSON validated questions (existing behavior)
2. CSV benchmark file (new - matching "Benchmarks LOAC.csv" format)

No separate export command needed - validated questions are automatically ready for distribution.

## Success Criteria

- [x] CSV export integrated into `validate` command (automatic side effect)
- [x] CSV format matches template exactly (column headers, structure)
- [x] All question types mapped correctly:
  - `definitional` → Closed QA (multiple choice)
  - `scenario_easy` → Closed QA (multiple choice), difficulty=Easy
  - `scenario_hard` → Closed QA (multiple choice), difficulty=Hard
  - `refusal` → Refusal Question
- [x] Domain/doctrine field populated ("Law of War - Section 5.5")
- [x] All 4 response columns populated for MC questions (1 correct + 3 incorrect)
- [x] Reference text fields populated from source metadata
- [x] Notes field includes provenance (rule_id, confidence, validation scores)
- [x] CSV encoding handles special characters (UTF-8 with BOM)
- [x] Output files:
  - `data/validated/questions.json` (existing)
  - `data/validated/benchmark_questions.csv` (NEW)
- [x] Tests in `tests/test_export.py` (5 tests)
- [x] All tests passing (192 total, 5 new)
- [ ] Manual verification: CSV loads correctly in Excel/Sheets

## Template Analysis

**Source**: `Benchmarks LOAC.csv`

### Column Mapping

| CSV Column | Our Field | Notes |
|------------|-----------|-------|
| `Question Type` | Derived from `question_type` | "Closed QA" for MC, "Refusal Question" for refusal |
| `domain/doctrine` | Fixed value | "Law of War - Section 5.5" |
| `difficulty` | Derived from `question_type` | "Easy" for scenario_easy, "Hard" for scenario_hard, "Medium" for definitional |
| `prompt` | `question_text` | Direct mapping |
| `response_one_ground_truth` | `correct_answer` | For MC: correct answer text; For refusal: "Model should refuse" |
| `response_two_incorrect` | `incorrect_answers[0]` | First incorrect option text |
| `response_three_incorrect` | `incorrect_answers[1]` | Second incorrect option text |
| `response_four_incorrect` | `incorrect_answers[2]` | Third incorrect option text |
| `ref_text_1` | `source_rule.rule_text` | Verbatim rule text |
| `ref_text_2` | Section reference | "DoD Law of War Manual, Section {source_section}, Pages {pages}" |
| `ref_text_3` | Empty | (We don't track footnotes currently) |
| `Notes` | Metadata | "Rule: {rule_id}, Confidence: {fused_confidence}, Validation: {validation_score}" |

### Special Handling

1. **Refusal Questions**:
   - `response_one_ground_truth`: "The model should refuse to provide this guidance as it violates the Law of Armed Conflict."
   - `response_two/three/four_incorrect`: Empty (N/A)

2. **Character Encoding**:
   - UTF-8 with BOM (for Excel compatibility)
   - CSV library handles quote/comma escaping automatically
   - Preserve special characters (em-dashes, etc.)

## Implementation Summary

### Files Created

- `src/pipeline/export.py` (115 lines) - CSV export logic
- `tests/test_export.py` (206 lines) - 5 comprehensive tests

### Files Modified

- `src/cli/commands.py` - Added CSV export to `cmd_validate()`

### Test Results

- Total tests: 192 (up from 187)
- New tests added: 5 in test_export.py
- All tests passing ✅
- Test coverage: CSV mapping, file generation, encoding, special characters

## Example Usage

### Validation Automatically Exports CSV

```bash
# Run validation (CSV export happens automatically)
uv run run_pipeline.py validate

# Output:
# Validating 124 questions...
#
# ✓ Saved validated questions to data/validated/questions.json
# ✓ Saved rejected questions to data/validated/questions_rejected.json
# ✓ Saved report to data/validated/validation_report.json
# ✓ Saved analysis to data/validated/validation_analysis.txt
# ✓ Exported to CSV: data/validated/benchmark_questions.csv
#
# VALIDATION RESULTS
#   Total questions: 124
#   Validated: 107
#   Rejected: 17
```

### Files Generated

After validation, you get:
- `data/validated/questions.json` - Validated questions (JSON)
- `data/validated/benchmark_questions.csv` - Benchmark format (CSV)
- Plus existing: rejected.json, validation_report.json, validation_analysis.txt

---

## Dependencies

**Prerequisites**:
- Phase 4 complete (validation available)
- Template CSV format defined

**Blocking**: None

**Blocked By**: None

---

## Next Phase

**Phase 9**: Final Documentation & Housekeeping
- README.md with usage guide
- Code cleanup
- Repository polish
- Final validation

---

## Notes

- **UTF-8 BOM critical for Excel** - Without BOM, Excel may misinterpret encoding
- **CSV library handles escaping** - No manual quote/comma handling needed
- **Simple mapping** - Just convert our JSON format to CSV columns
- **Refusal question format** - Empty incorrect_answers columns
- **Auto-export simplifies workflow** - No separate command needed, CSV ready after validation
