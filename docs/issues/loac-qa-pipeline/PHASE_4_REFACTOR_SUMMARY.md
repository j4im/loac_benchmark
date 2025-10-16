# Phase 4 Refactor Summary

**Date**: 2025-10-15
**Status**: Complete
**Tests**: 85/85 passing

## Overview

Refactored Phase 4 validation to add question entailment checking and simplify scoring from complex weighted formulas to simple threshold-based validation.

## Changes Made

### 1. New Question Entailment Validation

**Added**: `validate_question_entailment()` function in `src/pipeline/validate.py`

- Validates that the **question itself** is grounded in the source rule
- Applies to ALL question types (MC and refusal)
- Previously only validated answers, not questions

**New Prompt**: `QUESTION_ENTAILMENT_VALIDATION_PROMPT` in `src/config.py`

### 2. Separated Answer Entailment

**Renamed**: `validate_entailment()` → `validate_answer_entailment()`

- Now explicitly validates that the **answer** follows from the rule
- Only applies to MC questions (definitional, scenario_easy, scenario_hard)
- Renamed for clarity vs. question entailment

**Updated Prompt**: `ENTAILMENT_VALIDATION_PROMPT` → `ANSWER_ENTAILMENT_VALIDATION_PROMPT`

### 3. Simplified Scoring Logic

**Old System** (Complex Weighted):
```
Quality Score = 20% fused_confidence + 80% validation_score

Where:
- fused_confidence = (rule_conf × question_conf) / 100
- validation_score = 50% entailment + 50% distractors (MC)
                    OR 100% refusal (refusal questions)
- Threshold: ≥80 composite score
```

**New System** (Simple Thresholds):
```
Components (all must be ≥90%):
1. rule_confidence (from Phase 2)
2. question_confidence (from Phase 3)
3. question_entailment (ALL questions)
4. answer_entailment (MC only)
5. distractor_quality (MC only, average of 3)
6. refusal_appropriateness (refusal only)

Thresholds:
- Each component: ≥90%
- Mean of all components: ≥95%
```

### 4. Updated Functions

**Modified**:
- `calculate_fused_confidence()` → `get_rule_confidence()` (simpler, no multiplication)
- `calculate_validation_score()` → Removed (logic integrated into quality_score)
- `calculate_quality_score()` → Returns `(passes: bool, breakdown: dict)` instead of numeric score
- `validate_and_filter_questions()` → Updated to call new validation functions

### 5. Test Updates

**Updated**: `tests/test_validate.py`
- Renamed test class: `TestCalculateFusedConfidence` → `TestGetRuleConfidence`
- Removed: `TestCalculateValidationScore` (obsolete)
- Updated: `TestCalculateQualityScore` with new threshold-based tests
- All 85 tests passing (21 in test_validate.py)

## Validation Pipeline Flow

### Before
1. Structural validation (hard gate)
2. Answer entailment (MC only)
3. Distractor validation (MC only)
4. Refusal validation (refusal only)
5. Calculate fused confidence (rule × question)
6. Calculate validation score (weighted LLM results)
7. Calculate quality score (20% fused + 80% validation)
8. Filter by threshold (≥80)

### After
1. Structural validation (hard gate)
2. **Question entailment (ALL questions)** ← NEW
3. Answer entailment (MC only)
4. Distractor validation (MC only)
5. Refusal validation (refusal only)
6. Calculate quality score with threshold logic:
   - Check each component ≥90%
   - Check mean ≥95%
7. Pass/fail based on thresholds

## Cache Files

**New cache files**:
- `cache/validation/{question_id}_question_entailment.json` (NEW - one per question)
- `cache/validation/{question_id}_answer_entailment.json` (renamed from `_entailment.json`)
- `cache/validation/{question_id}_distractors.json` (unchanged)
- `cache/validation/{question_id}_refusal.json` (unchanged)

## Expected Impact

### Stricter Filtering
- **Old**: 80% composite score (many ways to pass)
- **New**: 90% per component + 95% mean (stricter)
- **Result**: Likely more rejections, higher quality validated set

### Better Quality Signals
- Question grounding now validated (catches questions not addressed by rules)
- Clear component-level failures (easier debugging)
- No magic weights - interpretable thresholds

### Simplified Interpretation
- Boolean pass/fail per component
- Clear failure reasons
- Mean score easy to understand

## Files Modified

1. `src/config.py` - Added `QUESTION_ENTAILMENT_VALIDATION_PROMPT`, renamed `ANSWER_ENTAILMENT_VALIDATION_PROMPT`
2. `src/pipeline/validate.py` - Major refactor (see changes above)
3. `tests/test_validate.py` - Updated all tests for new logic
4. `run_pipeline.py` - No changes (API-compatible)

## Backward Compatibility

- `validate_and_filter_questions()` signature unchanged (API-compatible)
- `quality_threshold` parameter deprecated but kept for compatibility
- Output structure changed:
  - Old: `_validation.quality_score` (float 0-100)
  - New: `_validation.passes_threshold` (boolean), `_validation.mean_score` (float 0-100)

## Next Steps

1. Run full pipeline to validate all 124 questions
2. Review rejected questions
3. Update Phase 4 completion docs with new metrics
4. Compare old vs new validation results

## Rationale

Per user request, simplified from complex weighted formula to simple threshold system:
- Easier to reason about (90% and 95% thresholds vs 20%/80% weights)
- More transparent (component-level failures)
- Added missing validation (questions should be grounded in rules)
- All components treated equally (no artificial weighting)
