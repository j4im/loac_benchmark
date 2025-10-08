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

### Phase 1: Project Foundation & PDF Parsing
**Objective**: Set up project structure with `uv` and implement hierarchical PDF parsing

**Success Criteria**:
- [x] `uv` project initialized with minimal dependencies (pdfplumber, python-dotenv, pytest)
- [x] Clean directory structure (src/, data/, cache/, output/, tests/)
- [x] PDF parser extracts sections with hierarchy (section numbers, titles, parent-child)
- [x] Footnotes captured and associated with sections
- [x] Page numbers tracked for each section
- [x] Output: JSON structure matching guidance.md spec
- [x] Unit tests in `tests/test_extract.py` covering parser functions
- [x] All tests passing: `pytest tests/test_extract.py`
- [x] Manual verification: Parsed Section 5.5 structure is accurate

**Deliverable**: Working `src/extract.py` that parses Section 5.5 PDF into structured JSON + passing tests

**Estimated Commits**: 1-2

---

### Phase 2: LLM-Based Rule Extraction
**Objective**: Use GPT-4o to extract legal rules from parsed sections

**Success Criteria**:
- [ ] OpenAI client configured with API key from environment
- [ ] Rule extraction prompt implemented per guidance.md template
- [ ] Extracts rules with: rule_text, rule_type, summary, actors, conditions, confidence, footnote_refs
- [ ] Caching system saves API responses to avoid re-processing
- [ ] Cost tracking/logging for API usage
- [ ] Handles token limits gracefully (chunking if needed)
- [ ] Unit tests in `tests/test_extract.py` for rule extraction (mocking OpenAI calls)
- [ ] All tests passing
- [ ] Manual verification: Sample rules are accurately extracted

**Deliverable**: `src/extract.py` extended with `extract_rules()` function; cached rules in `cache/rules/` + passing tests

**Estimated Commits**: 1-2

---

### Phase 3: Question Generation Engine
**Objective**: Generate all 4 question types for each extracted rule

**Success Criteria**:
- [ ] Implements `generate_definitional()` with prompt from guidance.md
- [ ] Implements `generate_scenario()` with easy/hard difficulty modes
- [ ] Implements `generate_refusal()` with applicability check
- [ ] Each question includes full provenance metadata (source_section, source_rule, footnotes_used, etc.)
- [ ] Generates ~4 questions per rule (1 def + 2 scenario + 1 refusal if applicable)
- [ ] Questions cached immediately after generation
- [ ] Unit tests in `tests/test_generate.py` (mocking OpenAI calls)
- [ ] All tests passing
- [ ] Manual verification: Sample questions are high quality and traceable

**Deliverable**: `src/generate.py` with all question generation functions + passing tests

**Estimated Commits**: 2 (could split into stages 3A: definitional/scenario, 3B: refusal)

---

### Phase 4: Validation & Quality Control
**Objective**: Automated validation pipeline with quality scoring

**Success Criteria**:
- [ ] Structural validation (required fields, format consistency, section refs exist)
- [ ] LLM-based entailment verification (answer supported by source text)
- [ ] Distractor quality check (plausible but incorrect)
- [ ] Refusal appropriateness verification
- [ ] Quality scoring: accuracy, clarity, difficulty (0-100)
- [ ] Filter: only questions scoring >80 proceed to final set
- [ ] Unit tests in `tests/test_validate.py`
- [ ] All tests passing
- [ ] Manual verification: Low-quality questions are correctly filtered out

**Deliverable**: `src/validate.py` with full validation pipeline + passing tests

**Estimated Commits**: 1-2

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
│   ├── extract.py      # PDF parsing + rule extraction
│   ├── generate.py     # Question generation (all types)
│   ├── validate.py     # Validation pipeline
│   └── config.py       # Prompts, templates, constants
├── data/
│   ├── raw/            # Original PDF (symlink or copy)
│   ├── extracted/      # Parsed sections JSON
│   └── validated/      # Final validated questions
├── cache/
│   ├── rules/          # Cached rule extractions
│   └── questions/      # Cached question generations
├── output/             # Final JSON/CSV exports + eval results
├── logs/               # Pipeline execution logs
├── run_pipeline.py     # Main question generation pipeline
├── run_eval.py         # Evaluation runner
├── score_eval.py       # AI-as-a-judge scoring
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
- **Active Phase**: Phase 2 (LLM-Based Rule Extraction)
- **Last Update**: Phase 1 complete with all tests passing
- **Next Step**: Create PHASE_2_DETAILED.md when ready to execute

### Completed Phases
- [x] Phase 1: Project Foundation & PDF Parsing (12/12 tests passing)
- [ ] Phase 2: LLM-Based Rule Extraction
- [ ] Phase 3: Question Generation Engine
- [ ] Phase 4: Validation & Quality Control
- [ ] Phase 5: Orchestration & Export
- [ ] Phase 6: Evaluation Runner
- [ ] Phase 7: AI-as-a-Judge Scoring

### Lessons Learned

**Phase 1:**
- PDF parsing with pdfplumber works well for structured legal documents
- Multi-line section titles require special handling - stored full text in content, truncated titles acceptable for metadata
- pytest provides good test structure - used fixtures for shared test data (parsed_sections)
- uv automatically selected Python 3.9.6 (older than target 3.10+ but compatible)
- Simple footnote reference extraction sufficient for now - full footnote content can be added later if needed
- 12 unit tests give good coverage of parsing functionality without over-engineering

---

## Success Metrics

- **Coverage**: >90% of identified rules have at least one question
- **Quality**: >80% of generated questions pass validation
- **Diversity**: Balanced distribution across question types
- **Provenance**: 100% of questions traceable to source text with section + page numbers
- **Cost**: <$0.50 per validated question (guidance estimate: $30-50 for full manual, we're doing 1 section)

---

**Note**: This plan prioritizes correctness and traceability over speed. Each phase produces verifiable outputs with full provenance.
