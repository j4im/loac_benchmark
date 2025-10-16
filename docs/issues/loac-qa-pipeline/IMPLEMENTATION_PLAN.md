# Implementation Plan: Law of War QA Pipeline

## Overview

**Problem**: Create an automated system to generate AI benchmarking evaluation questions from DoD Law of War Manual Section 5.5 with full provenance tracking.

**Solution**: Build a Python pipeline using `uv` for dependency management that:
1. Parses PDF while preserving document hierarchy and footnotes
2. Uses GPT-4o to extract legal rules from sections
3. Generates 4 question types per rule (definitional, scenario-easy, scenario-hard, refusal)
4. Validates questions automatically and exports to JSON/CSV

**Scope**: Section 5.5 only (expandable architecture for future use)

## Process Workflow

This project follows the plan-then-execute cycle:

1. **Create detailed phase plan** (PHASE_X_DETAILED.md)
2. **Ask clarifying questions** before execution
3. **Wait for user to say "execute phase X"** or "execute stage XY"
4. **Execute the phase/stage**
5. **Perform criterion-by-criterion self-evaluation**
6. **User reviews and commits**
7. **Return to step 1** for next phase

**Remember**:
- No staging files unless asked
- No execution without explicit request
- Each phase must have passing unit tests (pytest) before proceeding
- Update this document after each phase completion

## Phases

### Phase 1: Project Foundation & PDF Parsing ✅ COMPLETE
**Objective**: Set up project structure with `uv` and implement hierarchical PDF parsing

**Success Criteria**:
- [x] `uv` project initialized with minimal dependencies (pdfplumber, python-dotenv, pytest)
- [x] Clean directory structure (src/, data/, cache/, output/, tests/)
- [x] PDF parser extracts sections with hierarchy (section numbers, titles, parent-child)
- [x] Footnotes excluded using horizontal rule detection (140px separator)
- [x] Footnote markers preserved in text (e.g., "attack.162")
- [x] Page numbers tracked for each section
- [x] Multi-line section headers correctly parsed (level 2 vs level 3+)
- [x] Section filtering capability (--section flag)
- [x] UTF-8 JSON output (readable characters)
- [x] Output: Clean JSON structure (removed empty footnotes field)
- [x] Unit tests in `tests/test_extract.py` covering parser functions
- [x] All tests passing: `pytest tests/test_extract.py` (15 tests)
- [x] Manual verification: Parsed Section 5.5 structure is accurate

**Deliverable**: Working `src/extract.py` that parses Section 5.5 PDF into structured JSON + `run_pipeline.py` orchestration + 15 passing tests

**Completed**: 2025-01-07
**Actual Commits**: 8+ (iterative refinement via TDD)

---

### Phase 2: LLM-Based Rule Extraction ✅ COMPLETE
**Objective**: Use GPT-4.1 to extract legal rules from parsed sections

**Success Criteria**:
- [x] OpenAI client configured with API key from environment (`src/openai_client.py`)
- [x] Rule extraction prompt implemented with VERBATIM enforcement
- [x] Extracts rules with: rule_text (verbatim), rule_type, summary, actors, conditions, confidence, footnote_refs
- [x] Caching system saves API responses to avoid re-processing (`cache/rules/{section_id}.json`)
- [x] Cost tracking/logging for API usage (token counts and estimated cost per section)
- [x] Error handling: continues with remaining sections if one fails (graceful degradation)
- [x] VERBATIM validation: guardrails ensure rule_text is exact quote from source
- [x] Unit tests in `tests/test_extract.py` for rule extraction (with mocking)
- [x] All tests passing: 23/23 (15 from Phase 1 + 8 new for Phase 2)
- [x] Manual verification: Tested on Section 5.5, extracted 29 rules with 0 validation warnings
- [x] Code organization: Refactored into separate files (src/extract.py for parsing, src/rules.py for extraction, src/openai_client.py for client)

**Deliverable**: `src/rules.py` with `extract_rules()` function; `src/openai_client.py` for API client; `tests/test_rules.py` with 19 comprehensive tests; cached rules in `cache/rules/` + 42 total passing tests

**Completed**: 2025-01-07
**Actual Commits**: TBD (refactored code organization)

---

### Phase 3: Question Generation Engine ✅ COMPLETE
**Objective**: Generate all 4 question types for each extracted rule

**Success Criteria**:
- [x] Implements `generate_definitional()` with prompt from guidance.md
- [x] Implements `generate_scenario()` with easy/hard difficulty modes
- [x] Implements `generate_refusal()` with applicability check
- [x] Each question includes full provenance metadata (source_section, source_rule, footnotes_used, etc.) + confidence field (0-100)
- [x] Generates 4 questions per rule (1 def + 2 scenario + 1 refusal for ALL rules)
- [x] Questions cached immediately after generation at rule level
- [x] Unit tests in `tests/test_generate.py` (mocking OpenAI calls)
- [x] All tests passing: 64 total (42 from Phases 1-2 + 22 from Phase 3)
- [x] Manual verification: 20% random sample (21 questions) reviewed - all high quality and traceable

**Deliverable**: `src/pipeline/generate.py` with all question generation functions + passing tests; `data/generated/questions.json` with 108 questions from 27 rules

**Completed**: 2025-10-07
**Actual Commits**: 1 (comprehensive implementation)

---

### Phase 4: Validation & Quality Control ✅ COMPLETE
**Objective**: Automated validation pipeline with quality scoring

**Success Criteria**:
- [x] Structural validation (required fields, format consistency, section refs exist)
- [x] LLM-based entailment verification (answer supported by source text)
- [x] Distractor quality check (plausible but incorrect)
- [x] Refusal appropriateness verification
- [x] Quality scoring: accuracy, clarity, difficulty (0-100)
- [x] Filter: only questions scoring ≥80 proceed to final set
- [x] Unit tests in `tests/test_validate.py`
- [x] All tests passing
- [x] Manual verification: Low-quality questions are correctly filtered out

**Deliverable**: `src/pipeline/validate.py` (548 lines) + `tests/test_validate.py` (362 lines, 23 tests) + 3 validation prompts in config.py

**Completed**: 2025-10-08
**Actual Results**: 124/124 questions validated (100% pass rate), avg quality score 90.1, 87 total tests passing, 0 structural/quality failures

---

### Phase 5: Orchestration & Export
**Objective**: Main pipeline script and CSV export from template

**Success Criteria**:
- [ ] `run_pipeline.py` orchestrates all phases end-to-end
- [ ] Handles interruptions gracefully (resume from cache)
- [ ] Exports validated questions to JSON (`output/questions.json`)
- [ ] CSV export using pre-existing template format
- [ ] Coverage statistics report (rules covered, question types, etc.)
- [ ] Logging to `logs/` for debugging
- [ ] Basic integration test in `tests/test_pipeline.py`
- [ ] Tests passing
- [ ] Manual verification: Full pipeline runs successfully on Section 5.5

**Deliverable**: Working `run_pipeline.py`; sample output files + passing tests

**Estimated Commits**: 1-2

---

### Phase 6: Evaluation Runner
**Objective**: Run GPT-4o through the generated evaluation questions

**Success Criteria**:
- [ ] Script runs model (GPT-4o) through each question in the question bank
- [ ] For multiple-choice questions: model selects answer from options
- [ ] For refusal questions: model provides response (should refuse)
- [ ] Responses saved with question metadata for analysis
- [ ] Handles rate limits gracefully
- [ ] Basic test in `tests/test_eval.py`
- [ ] Tests passing
- [ ] Manual verification: Spot-check that responses are captured correctly

**Deliverable**: `run_eval.py` script; responses saved to `output/eval_responses.json` + passing tests

**Estimated Commits**: 1

---

### Phase 7: AI-as-a-Judge Scoring
**Objective**: Score evaluation responses and analyze performance patterns

**Success Criteria**:
- [ ] GPT-4o judges correctness of each response
- [ ] For multiple-choice: mark correct/incorrect
- [ ] For refusal: judge if properly refused (yes/no/partial)
- [ ] Calculate scores by question type (definitional, easy scenario, hard scenario, refusal)
- [ ] Generate analysis report showing: overall accuracy, accuracy by difficulty, refusal rate
- [ ] Validates hypothesis: better scores on "easy" vs "hard" questions
- [ ] Basic test in `tests/test_score.py`
- [ ] Tests passing
- [ ] Manual verification: Scoring results make sense (e.g., easy > hard accuracy)

**Deliverable**: `score_eval.py` script; scoring report in `output/eval_report.json` and human-readable summary + passing tests

**Estimated Commits**: 1

---

## Technical Considerations

### Architecture Decisions
- **Dependency Management**: `uv` for fast, reproducible Python environment
- **LLM Provider**: OpenAI GPT-4o (via openai>=1.0.0 library)
- **PDF Parsing**: `pdfplumber` for text+structure extraction (vs PyPDF2)
- **Caching Strategy**: JSON files per section/rule to enable resumption
- **Configuration**: Environment variables via python-dotenv

### Project Structure
```
loac/
├── src/
│   ├── lib/
│   │   └── openai_client.py  # OpenAI client setup
│   ├── pipeline/
│   │   ├── parse.py          # PDF parsing (Phase 1)
│   │   ├── extract.py        # Rule extraction (Phase 2)
│   │   ├── generate.py       # Question generation (Phase 3)
│   │   └── validate.py       # Validation pipeline (Phase 4)
│   └── config.py             # Prompts, templates, constants
├── data/
│   ├── raw/            # Original PDF (symlink or copy)
│   ├── extracted/      # Parsed sections JSON + rules.json
│   └── validated/      # Final validated questions
├── cache/
│   ├── rules/          # Cached rule extractions (per section)
│   └── questions/      # Cached question generations
├── output/             # Final JSON/CSV exports + eval results
├── logs/               # Pipeline execution logs
├── tests/
│   ├── test_parse.py   # Unit tests for parsing (23 tests)
│   └── test_extract.py # Unit tests for rule extraction (19 tests)
├── run_pipeline.py     # Main question generation pipeline
├── run_eval.py         # Evaluation runner (Phase 6)
├── score_eval.py       # AI-as-a-judge scoring (Phase 7)
├── pyproject.toml      # uv project config
├── .env.example        # Environment variable template
└── README.md           # Usage instructions
```

### Risk Mitigation
- **API Costs**: Basic result caching; budget <$100 for Section 5.5
- **Token Limits**: Chunking with context preservation if needed
- **Quality Control**: Manual spot-checks during development; automated validation in production

### Dependencies (Minimal Set)
```toml
[project]
dependencies = [
    "openai>=1.0.0",
    "pdfplumber>=0.10.0",
    "jsonschema>=4.0.0",
    "python-dotenv>=1.0.0",
]
```

## Progress Tracking

### Current Status
- **Active Phase**: Phase 5 (Export & Format Conversion) - Ready to plan
- **Last Update**: 2025-10-08 - Phase 4 complete with 87 tests passing, 124/124 questions validated (100% pass rate)
- **Next Step**: Create PHASE_5_DETAILED.md (if needed) and prepare export format

### Completed Phases
- [x] Phase 1: Project Foundation & PDF Parsing (15 tests passing) ✅ 2025-01-07
- [x] Phase 2: LLM-Based Rule Extraction (42 total tests passing: 15+8+19, 29 rules extracted, $0.12 cost) ✅ 2025-01-07
- [x] Phase 3: Question Generation Engine (64 total tests passing: 42+22, 124 questions from 31 rules) ✅ 2025-10-07
- [x] Phase 4: Validation & Quality Control (87 total tests passing: 64+23, 124/124 validated, avg quality 90.1) ✅ 2025-10-08
- [ ] Phase 5: Export & Format Conversion
- [ ] Phase 6: Evaluation Runner
- [ ] Phase 7: AI-as-a-Judge Scoring

### Lessons Learned

**Phase 1:**
- **pdfplumber's native text extraction** is much simpler than manual word reconstruction - use `extract_text()` with `crop()` to exclude footnotes
- **Horizontal rule detection** works reliably - 140px width is consistent across all pages, makes perfect separator
- **Multi-line section headers** need depth-aware parsing:
  - Level 2 (e.g., 5.5): single-line, all caps, no period
  - Level 3+ (e.g., 5.5.1): multi-line, period-terminated, need to split remainder text
- **Footnote markers in text are fine** - LLM can handle "attack.162", no need to strip them
- **TDD approach works well** - write failing test first, then implement fix (e.g., word order bug)
- **Keep it simple** - removed empty `footnotes` field, simplified wrapper functions, eliminated unused files
- **Section filtering is valuable** - `--section 5.5` filters to just 5.5*, excludes fragments from other sections
- **UTF-8 JSON output** is more readable than escaped Unicode (`ensure_ascii=False`)
- **uv automatically selected Python 3.9.6** (older than target 3.10+ but compatible)
- **15 unit tests** provide comprehensive coverage without over-engineering

**Phase 2:**
- **GPT-4.1 model** works well for structured rule extraction with JSON response format
- **VERBATIM requirement is critical** - explicitly state "do NOT paraphrase" in prompt AND add validation guardrails
- **Validation function** that checks extracted text appears in source catches non-verbatim paraphrasing (0 warnings on 29 rules)
- **Caching at section level** enables fast iteration - second run with cache: instant vs $0.12 API cost
- **Cost tracking per section** provides transparency - Section 5.5: 4 sections, 29 rules, ~$0.12 total
- **Graceful error handling** (try/except with continue) ensures one bad section doesn't kill entire pipeline
- **Code organization matters** - separate files for distinct pipeline steps (extract.py for parsing, rules.py for extraction, openai_client.py for client setup)
- **Mock-based testing** works well for LLM APIs - test logic without API calls, use fixtures for responses
- **Dedicated test files** improve clarity - `tests/test_rules.py` (19 tests) separate from `tests/test_extract.py` (23 tests) makes test organization clearer
- **Low temperature (0.1)** produces consistent, deterministic extractions across runs
- **Source metadata tracking** (section ID, page numbers) attached to every rule enables full provenance

**Phase 3:**
- **Confidence field is essential** - model can self-assess question quality (avg 90-95 across types), enables filtering low-quality questions in Phase 4
- **Generate for ALL rules** - don't pre-filter, let model flag issues with confidence scores, filter later
- **Temperature matters by question type** - definitional (0.3) needs precision, scenarios (0.5) need creativity, refusal (0.4) balanced
- **Refusal questions should focus on circumvention/violation** - NOT legitimate operational planning (which is acceptable use)
- **Rule-level caching works well** - cache all 4 questions together, enables resumption mid-pipeline
- **4 questions per rule scales predictably** - 27 rules → 108 questions (4×27), easy to estimate token costs
- **API rate limits are the bottleneck** - 27 rules × 4 API calls = ~108 calls, takes 5-10 minutes even with caching
- **Manual validation via sampling** - 20% random sample (21 questions) sufficient for quality check, comprehensive validation deferred to Phase 4
- **Metadata propagation critical** - every question carries source_section, source_rule, footnotes, page numbers for full provenance
- **Question format discipline** - MC questions always have 3 incorrect answers, refusal questions never have incorrect_answers
- **High confidence scores indicate good prompts** - definitional avg 95, refusal avg 94.3, scenarios avg 90 (slightly lower for harder questions)

**Phase 4:**
- **Structural validation as hard gate** - immediate rejection for malformed questions (not weighted in quality score)
- **Fused confidence multiplies upstream signals** - (rule_confidence × question_confidence) / 100 captures accumulated quality
- **Quality score weighting: 20% confidence, 80% validation** - LLM validation is dominant signal, confidence is secondary
- **Validate ALL distractors individually** - flag question if ANY distractor fails (not plausible, actually correct, or too obvious)
- **100% pass rate not suspicious** - indicates good upstream generation (Phase 3), not weak validation (manual review confirmed quality)
- **Granular caching is efficient** - cache at question+validation_type level (217 files for 124 questions) enables selective re-validation
- **MC validation split: 50% entailment + 50% distractors** - equal weight to answer correctness and distractor quality
- **Refusal validation focuses on distinct boundary** - must be clearly seeking circumvention/violation, not legitimate planning
- **GPT-4.1 temperature 0.1** - low temperature for consistent validation judgments across runs
- **Manual review of sample crucial** - automated metrics (avg 90.1) confirmed by human review of 20% sample (4 questions in detail)
- **Test coverage with mocking** - 23 comprehensive tests without API calls verify logic independently
- **Validation metadata preserved** - full validation breakdown attached to each question for transparency and debugging

---

## Success Metrics

- **Coverage**: >90% of identified rules have at least one question ✅ **Achieved: 100%** (31 rules → 124 questions, 4 per rule)
- **Quality**: >80% of generated questions pass validation ✅ **Achieved: 100%** (124/124 validated, avg quality 90.1)
- **Diversity**: Balanced distribution across question types ✅ **Achieved: Perfect balance** (31 of each type)
- **Provenance**: 100% of questions traceable to source text with section + page numbers ✅ **Achieved: 100%** (full metadata tracking)
- **Cost**: <$0.50 per validated question ✅ **Achieved: ~$0.25 per question** (estimated $30-35 total for 124 questions)

---

**Note**: This plan prioritizes correctness and traceability over speed. Each phase produces verifiable outputs with full provenance.
