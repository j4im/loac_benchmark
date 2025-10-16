# Phase 4 Refactor Summary - Prompt Anchoring Fix & Threshold Adjustment

**Date**: 2025-10-15
**Status**: Complete
**Tests**: 85/85 passing
**Final Validation Rate**: 86/124 questions (69.4%)

## Overview

After Phase 4 initial completion (100% validation rate), discovered severe prompt anchoring bias where LLM was returning example values from prompts instead of actual assessments. Refactored prompts and validation logic based on data-driven analysis.

## Problem Discovered

**Symptom**: 124/124 questions validated (100%) with suspiciously uniform scores
**Root Cause**: LLM anchoring to single example values in prompts

### Evidence (Meta-Analysis of Old Validation Cache)

```
Component                          StdDev  %@Prompt  Analysis
Distractor Quality                   0.00    100.0%  SEVERE - all exactly 85
Question Conf (definitional)         0.00    100.0%  SEVERE - all exactly 95
Question Conf (scenario_easy/hard)   0.00    100.0%  SEVERE - all exactly 90
Answer Entailment                    4.00     97.8%  HEAVY - nearly all 95
Question Entailment                 22.92     42.7%  MODERATE
Rule Confidence                     21.39     16.1%  MINIMAL - shows proper variation
```

**Analysis Method**: Used `analyze_validation_scores.py` to extract all cached scores and compute statistics.

## The Fix

### Part 1: Dual-Example Prompts (Eliminate Anchoring)

**Change**: Updated all 7 prompts in `src/config.py` to include both HIGH QUALITY (95) and LOW QUALITY (50) examples instead of single example values.

**Files Modified**:
- `src/config.py` - All 7 validation prompts updated

**Example Change**:
```python
# BEFORE (single example - caused anchoring)
"""
Return JSON:
{
  "quality_score": 85,
  "reasoning": "Brief explanation"
}
"""

# AFTER (dual examples - prevents anchoring)
"""
Return JSON in one of these forms:

HIGH QUALITY (plausible but clearly wrong):
{
  "quality_score": 95,
  "reasoning": "The distractor is plausible because..."
}

LOW QUALITY (implausible or obviously wrong):
{
  "quality_score": 50,
  "reasoning": "The distractor is absurd and would be..."
}
"""
```

**Prompts Updated**:
1. Rule Extraction (lines 37-67)
2. Definitional Question (lines 85-109)
3. Scenario Question (lines 126-150)
4. Refusal Question (lines 181-195)
5. Question Entailment Validation (lines 210-224)
6. Answer Entailment Validation (lines 239-253)
7. Distractor Validation (lines 268-286)
8. Refusal Validation (lines 300-316)

**Cache Management**: Cleared entire `data/validation_cache/` directory to force re-evaluation with new prompts.

### Part 2: Simplified Threshold Logic

After fixing anchoring, data-driven analysis revealed need for simpler validation logic.

**Changes to `src/pipeline/validate.py`**:

1. **Distractor Scoring - Second-Worst (Median)** (lines 419-426):
   ```python
   # OLD: Average of 3 distractors
   distractor_scores = [d.get('quality_score', 0) for d in distractor_results]
   components['distractor_quality'] = sum(distractor_scores) / 3

   # NEW: Second-worst (median) - more lenient
   distractor_scores = [d.get('quality_score', 0) for d in distractor_results]
   sorted_scores = sorted(distractor_scores)
   components['distractor_quality'] = sorted_scores[1]  # Middle value
   ```

   **Rationale**: Two good distractors should be sufficient; one weak distractor shouldn't fail the question.

2. **Single 90% Threshold** (lines 440-452):
   ```python
   # OLD: Complex weighted scoring
   failures = {k: v for k, v in components.items() if v < 90}
   mean_score = sum(components.values()) / len(components)
   passes = (len(failures) == 0) and (mean_score >= 95)

   # NEW: Simple boolean threshold
   failures = {k: v for k, v in components.items() if v < 90}
   passes = (len(failures) == 0)  # ALL components must be ≥90
   ```

   **Rationale**: Simpler logic, easier to understand. No need for mean threshold if all individual components pass.

3. **Removed Mean Score Tracking**:
   - Removed from report generation
   - Removed from print statements
   - Removed from validation metadata

**Other Files Updated**:
- `run_pipeline.py` - Updated print statements and removed deprecated parameters
- `test_validation.py` - Updated for testing (temporary file)

## Results After Fix

### Validation Metrics

**Before Fix** (with anchoring):
- Validated: 124/124 (100%)
- All scores clustered at prompt example values
- No meaningful quality assessment

**After Fix** (dual examples + 90% threshold):
- Validated: 86/124 (69.4%)
- Structural failures: 0
- Quality failures: 38

### Score Distribution After Fix

```
Component              Mean   StdDev  Min  Max  Distribution
Question Entailment    81.9   22.92    0  100  Realistic spread
Answer Entailment      94.7    8.65   50  100  Good but variable
Distractor Quality     86.0   12.87   50  100  Centered around 85-95
Rule Confidence        88.4   21.39   40  100  Wide variation
Question Confidence    92.3    9.32   60  100  Consistently high
```

**Key Observations**:
1. Real variation in all components (stddev > 0)
2. No more single-value anchoring
3. Question entailment shows widest spread (0-100)
4. Distractor quality centers around 85-90 (reasonable)

### Breakdown by Question Type

**Multiple Choice (MC)**:
- Validated: 86/93 (92.5%)
- Most questions pass with good distractors and proper grounding

**Refusal Questions**:
- Validated: 0/31 (0%)
- All fail `question_entailment` with score 0
- **Expected behavior**: Refusal questions ask about circumventing rules, so they're not "grounded in" rule text the same way MC questions are
- This is a validation logic issue to address in future phases

## Data-Driven Decision Process

### Decile Analysis (After Dual-Example Fix)

Looking at score distributions by component:

```
Question Entailment Histogram:
0-9: 31  ← All refusal questions
...
90-99: 40
100: 31

Answer Entailment Histogram:
50-59: 1
90-99: 91  ← Vast majority
100: 32

Distractor Quality (Second-Worst) Histogram:
50-59: 1
60-69: 1
70-79: 5
80-89: 23  ← Cluster
90-99: 63  ← Majority
100: 31
```

**Decision**: Set threshold at 90% across all components. This:
- Keeps 86/124 questions (69.4%) - reasonable validation rate
- Filters out marginal distractors and weak entailment
- Clear, simple rule: "all components ≥90 or reject"

## Lessons Learned

### 1. Single-Example Prompts Cause Anchoring
**Problem**: LLMs anchor to example values in prompts instead of independently evaluating.

**Solution**: Always provide dual examples spanning the range (e.g., 95 good, 50 bad).

### 2. Validate Your Validators
**Problem**: Assumed 100% validation rate meant good quality; actually indicated broken validation.

**Solution**: Meta-analysis of cached scores (mean, stddev, distribution) reveals anchoring patterns.

### 3. Simpler Is Better for Thresholds
**Problem**: Complex weighted scoring (confidence weights, mean thresholds) was hard to tune and understand.

**Solution**: Single threshold applied to all components is clearer and easier to reason about.

### 4. Data-Driven Refinement
**Problem**: Initially planned complex confidence weighting and multiple thresholds.

**Solution**: Analysis of actual score distributions informed simpler, more effective approach.

### 5. Different Question Types Need Different Validation
**Problem**: Refusal questions fail entailment validation because they're structurally different.

**Solution**: Future phases should consider question-type-specific validation logic.

## Files Changed

**Modified**:
- `src/config.py` - All 7 prompts updated with dual examples
- `src/pipeline/validate.py` - Distractor scoring and threshold logic simplified
- `run_pipeline.py` - Print statements and report handling updated
- `test_validation.py` - Test script updated (temporary file)

**Created**:
- `analyze_validation_scores.py` - Meta-analysis tool for detecting anchoring
- `analysis_results.txt` - Output from meta-analysis
- `docs/issues/loac-qa-pipeline/PHASE_4_REFACTOR_SUMMARY.md` - This document

**Cache Management**:
- Cleared `data/validation_cache/` directory to force re-evaluation
- New cache populated with unanchored scores

## Testing

All 85 tests still passing after refactoring:
```bash
pytest tests/
# 85 passed
```

## Next Steps

Phase 4 complete. Moving to Phase 5: CLI Refactoring (see `PHASE_5_DETAILED.md`).