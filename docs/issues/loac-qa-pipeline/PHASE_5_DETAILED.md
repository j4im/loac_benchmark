# Phase 5: CLI Refactoring & Pipeline Orchestration

**Status**: Planning
**Started**: 2025-10-15
**Objective**: Transform `run_pipeline.py` into a production-grade git-style CLI with subcommands, proper caching, and filtering capabilities

## Overview

Refactor the monolithic `run_pipeline.py` into a modular CLI tool following established patterns (git, docker, kubectl) with:
- Subcommand architecture for each pipeline stage
- Global options (verbose, dry-run, cache control)
- Per-command filtering and configuration
- Improved developer experience and debuggability

## Success Criteria

- [ ] Git-style CLI with 5 subcommands: `all`, `parse`, `rules`, `questions`, `validate`
- [ ] Global options work across all commands: `--verbose`, `--dry-run`, `--clean-cache`, `--ignore-cache`
- [ ] `--dry-run` mode prints LLM prompts without API calls
- [ ] `--verbose` mode logs all LLM interactions to stdout
- [ ] `--clean-cache` deletes relevant cache files and exits
- [ ] Filtering works: `--section PREFIX`, `--rule-id PATTERN`, `--question-id PATTERN`
- [ ] Rule IDs added during Phase 2 (format: `{section}_r{index}`)
- [ ] Backward compatible with existing data files
- [ ] All 87 existing tests still pass
- [ ] New tests for CLI argument parsing (minimum 10 tests)
- [ ] Updated README.md with CLI usage examples
- [ ] Help text (`-h`) clear and comprehensive for each command

## CLI Design Specification

### Command Structure

```bash
run_pipeline [global-options] <command> [command-options]
```

### Global Options

Apply to all commands, processed before subcommand execution:

```
-h, --help              Show help message and exit
-v, --verbose           Print all LLM prompts and responses to stdout
-d, --dry-run          Print LLM commands without executing (implies --verbose)
--clean-cache          Delete cache files for this command, then exit
--ignore-cache         Don't read or write cache (fresh run, no persistence)
--config FILE          Override default config file path
```

**Behavior Notes**:
- `--dry-run` mocks `openai.chat.completions.create()` to print prompt text
- `--clean-cache` deletes cache based on command context (e.g., `validate` → `cache/validation/*`)
- `--ignore-cache` runs fresh but doesn't delete existing cache
- `--verbose` logs: timestamp, command, model, tokens, cost estimate, full prompt/response

### Subcommands

#### 1. `all` - Run Full Pipeline

Execute all stages in sequence: parse → rules → questions → validate

```bash
run_pipeline all [options]
```

**Options**:
```
--pdf PATH              Input PDF file (default: data/raw/section_5_5.pdf)
--section PREFIX        Filter to sections starting with PREFIX (e.g., "5.5")
--output-dir PATH       Output directory root (default: data/)
--resume                Skip stages with existing output files
```

**Example**:
```bash
# Full pipeline on section 5.5
run_pipeline all --section 5.5

# Full pipeline with verbose logging
run_pipeline -v all --pdf manual.pdf

# Dry-run to see what would be done
run_pipeline -d all --section 5.5.2
```

**Output**:
- `data/extracted/sections.json` - Parsed sections
- `data/extracted/rules.json` - Extracted rules
- `data/generated/questions.json` - Generated questions
- `data/validated/questions.json` - Validated questions
- `data/validated/validation_report.json` - Validation summary

---

#### 2. `parse` - Extract Sections from PDF

Parse PDF and extract hierarchical section structure

```bash
run_pipeline parse [options]
```

**Options**:
```
--pdf PATH              Input PDF file (REQUIRED)
--section PREFIX        Filter to sections starting with PREFIX
--output PATH           Save parsed sections JSON (default: data/extracted/sections.json)
```

**Example**:
```bash
# Parse entire PDF
run_pipeline parse --pdf data/raw/manual.pdf

# Parse only section 5.5 subsections
run_pipeline parse --pdf manual.pdf --section 5.5
```

**Cache**: `cache/parse/{pdf_hash}.json` (hash of PDF path + mtime)

---

#### 3. `rules` - Extract Legal Rules from Sections

Use GPT-4.1 to extract legal rules from parsed sections

```bash
run_pipeline rules [options]
```

**Options**:
```
--input PATH            Parsed sections JSON (default: data/extracted/sections.json)
--section PREFIX        Filter which sections to process
--output PATH           Save rules JSON (default: data/extracted/rules.json)
```

**Example**:
```bash
# Extract rules from all sections
run_pipeline rules

# Extract rules only from 5.5.2
run_pipeline rules --section 5.5.2

# Regenerate rules for section 5.5 (clear cache first)
run_pipeline --clean-cache rules --section 5.5
run_pipeline rules --section 5.5
```

**Cache**: `cache/rules/{section_id}.json` (one file per section)

**Rule ID Format**: `{section}_r{index}` (e.g., "5.5_r0", "5.5.2_r3")
- Added during extraction
- Enables downstream filtering
- Included in rule JSON: `"rule_id": "5.5_r0"`

---

#### 4. `questions` - Generate Questions from Rules

Generate evaluation questions (4 types per rule)

```bash
run_pipeline questions [options]
```

**Options**:
```
--input PATH            Rules JSON (default: data/extracted/rules.json)
--rule-id PATTERN       Filter rules by glob pattern (e.g., "5.5_r0", "5.5.2_*")
--types TYPES           Comma-separated question types (default: all)
                        Choices: def,easy,hard,refusal
--output PATH           Save questions JSON (default: data/generated/questions.json)
```

**Example**:
```bash
# Generate all question types for all rules
run_pipeline questions

# Generate only for rule 5.5_r0
run_pipeline questions --rule-id "5.5_r0"

# Generate only definitional and scenario-easy questions
run_pipeline questions --types def,easy

# Regenerate questions for all 5.5.2 rules
run_pipeline --clean-cache questions --rule-id "5.5.2_*"
run_pipeline questions --rule-id "5.5.2_*"
```

**Cache**: `cache/questions/{rule_id}_{question_type}.json` (one file per question)

**Filtering Logic**: Uses `fnmatch` for glob patterns
- `"5.5_r0"` → exact match
- `"5.5_*"` → all rules in section 5.5
- `"5.5.2_*"` → all rules in section 5.5.2
- `"*_r0"` → first rule of every section

---

#### 5. `validate` - Validate Generated Questions

Run quality validation on generated questions

```bash
run_pipeline validate [options]
```

**Options**:
```
--input PATH            Questions JSON (default: data/generated/questions.json)
--question-id PATTERN   Filter questions by glob pattern (e.g., "*_refusal")
--output PATH           Validated questions JSON (default: data/validated/questions.json)
--threshold N           Quality threshold 0-100 (default: 90)
```

**Example**:
```bash
# Validate all questions
run_pipeline validate

# Validate only refusal questions
run_pipeline validate --question-id "*_refusal"

# Validate with stricter threshold
run_pipeline validate --threshold 95

# Re-validate all questions (ignore cache)
run_pipeline --ignore-cache validate
```

**Cache**: `cache/validation/{question_id}_{validation_type}.json`
- Validation types: `question_entailment`, `answer_entailment`, `distractors`, `refusal`

---

## Implementation Plan

### Stage 5A: Refactor to Subcommand Architecture

**Tasks**:
1. Create `src/cli/` module:
   - `__init__.py` - CLI entry point
   - `parser.py` - Argparse setup with subparsers
   - `commands.py` - Command handler functions
   - `utils.py` - Shared utilities (verbose logging, dry-run mocking, cache mgmt)

2. Update `run_pipeline.py`:
   - Import from `src.cli`
   - Call CLI entry point
   - Maintain backward compatibility (detect if run with no args → interactive mode)

3. Implement global options:
   - `--verbose`: context manager that captures/logs all LLM calls
   - `--dry-run`: monkey-patch `openai.chat.completions.create` with mock
   - `--clean-cache`: delete cache based on command + filters
   - `--ignore-cache`: set global flag checked by caching functions

4. Implement each subcommand handler:
   - `cmd_all()` - orchestrates full pipeline
   - `cmd_parse()` - calls `parse_document()`
   - `cmd_rules()` - calls `extract_rules()`
   - `cmd_questions()` - calls `generate_questions_for_rule()`
   - `cmd_validate()` - calls `validate_and_filter_questions()`

**Deliverables**:
- `src/cli/` module (4 files, ~400 lines total)
- Refactored `run_pipeline.py` (~50 lines)
- All existing functionality preserved

---

### Stage 5B: Add Rule IDs and Filtering

**Tasks**:
1. Update `src/pipeline/extract.py`:
   - Add `rule_id` field during rule extraction
   - Format: `f"{section_id}_r{index}"`
   - Example: Section "5.5" rule #0 → `"rule_id": "5.5_r0"`

2. Implement filtering functions in `src/cli/utils.py`:
   - `filter_sections(sections, prefix)` - filter by section prefix
   - `filter_rules(rules, pattern)` - filter by rule_id glob pattern
   - `filter_questions(questions, pattern)` - filter by question_id glob pattern

3. Integrate filtering into command handlers:
   - Parse: filter sections before processing
   - Rules: filter sections, then extract rules
   - Questions: filter rules, then generate questions
   - Validate: filter questions, then validate

**Deliverables**:
- Rule IDs in `data/extracted/rules.json`
- Filtering utilities (~100 lines)
- Updated command handlers to use filtering

---

### Stage 5C: Implement Verbose and Dry-Run Modes

**Tasks**:
1. Verbose mode (`--verbose`):
   - Create `LLMLogger` context manager
   - Intercept `openai.chat.completions.create()` calls
   - Log: timestamp, model, prompt (truncated to 500 chars), response, tokens, cost
   - Write to stdout with clear formatting

2. Dry-run mode (`--dry-run`):
   - Create `DryRunMock` class
   - Mock `openai.chat.completions.create()` to:
     - Print full prompt to stdout
     - Return mock response (empty JSON `{}`)
   - Implies `--verbose`
   - Commands should handle empty responses gracefully

**Deliverables**:
- `LLMLogger` class (~50 lines)
- `DryRunMock` class (~30 lines)
- Integration in CLI entry point

---

### Stage 5D: Implement Cache Management

**Tasks**:
1. `--clean-cache` option:
   - Delete cache files based on command:
     - `parse`: `cache/parse/*`
     - `rules`: `cache/rules/*` (optionally filtered by `--section`)
     - `questions`: `cache/questions/*` (optionally filtered by `--rule-id`)
     - `validate`: `cache/validation/*` (optionally filtered by `--question-id`)
   - Print what was deleted
   - Exit after cleaning (don't run command)

2. `--ignore-cache` option:
   - Set global flag: `config.IGNORE_CACHE = True`
   - Update all caching functions to check flag:
     - Skip reading from cache
     - Skip writing to cache
   - Existing data not deleted (vs `--clean-cache`)

**Deliverables**:
- Cache management functions (~100 lines)
- Updated caching logic in all pipeline modules

---

### Stage 5E: Testing and Documentation

**Tasks**:
1. Write CLI tests in `tests/test_cli.py`:
   - Argument parsing (10+ tests)
   - Filtering logic (8+ tests)
   - Verbose/dry-run integration (5+ tests)
   - Cache management (5+ tests)
   - Total: 30+ new tests

2. Update `README.md`:
   - Remove old usage instructions
   - Add new CLI usage section with examples
   - Document all commands and options
   - Add common workflows (e.g., "regenerate questions for one section")

3. Add `run_pipeline --help` text:
   - Clear descriptions for all commands
   - Examples for each command
   - Tips for common use cases

**Deliverables**:
- `tests/test_cli.py` (30+ tests)
- Updated `README.md`
- Comprehensive help text

---

## File Structure After Phase 5

```
loac/
├── src/
│   ├── cli/
│   │   ├── __init__.py      # CLI entry point
│   │   ├── parser.py        # Argparse configuration
│   │   ├── commands.py      # Command handlers (cmd_all, cmd_parse, etc.)
│   │   └── utils.py         # Filtering, verbose, dry-run, cache mgmt
│   ├── lib/
│   │   └── openai_client.py
│   ├── pipeline/
│   │   ├── parse.py
│   │   ├── extract.py       # Updated: adds rule_id
│   │   ├── generate.py
│   │   └── validate.py
│   └── config.py
├── data/
│   ├── extracted/
│   │   ├── sections.json
│   │   └── rules.json       # Updated: includes rule_id field
│   ├── generated/
│   │   └── questions.json
│   └── validated/
│       ├── questions.json
│       └── validation_report.json
├── cache/
│   ├── parse/
│   ├── rules/
│   ├── questions/
│   └── validation/
├── tests/
│   ├── test_parse.py
│   ├── test_extract.py
│   ├── test_generate.py
│   ├── test_validate.py
│   └── test_cli.py          # NEW: 30+ tests for CLI
├── run_pipeline.py          # Refactored: thin wrapper around src.cli
└── README.md                # Updated: new CLI documentation
```

---

## Example Workflows

### Workflow 1: Full Pipeline Run

```bash
# Run everything with verbose logging
run_pipeline -v all --section 5.5
```

### Workflow 2: Iterative Question Development

```bash
# 1. Generate questions for one rule
run_pipeline questions --rule-id "5.5_r0"

# 2. Validate to see results
run_pipeline validate --question-id "5.5_r0_*"

# 3. If not satisfied, regenerate (clear cache first)
run_pipeline --clean-cache questions --rule-id "5.5_r0"
run_pipeline questions --rule-id "5.5_r0"

# 4. Re-validate
run_pipeline validate --question-id "5.5_r0_*"
```

### Workflow 3: Debug LLM Prompts

```bash
# Dry-run to see prompts without API calls
run_pipeline -d questions --rule-id "5.5_r0" --types def
```

### Workflow 4: Regenerate Validation Only

```bash
# Re-validate all questions with fresh LLM calls
run_pipeline --clean-cache validate
run_pipeline validate
```

### Workflow 5: Process Specific Subsection

```bash
# Full pipeline for only 5.5.2
run_pipeline all --section 5.5.2
```

---

## Backward Compatibility

**Existing Data Files**:
- `data/extracted/rules.json` without `rule_id` → auto-generate on load
- Cache files unchanged (still work as-is)
- Output formats unchanged

**Existing Scripts**:
- `test_validation.py` → still works (doesn't use CLI)
- Direct imports of pipeline modules → still work

**Migration**:
- Re-run `run_pipeline rules` to add `rule_id` to existing rules.json
- No data loss or re-generation required

---

## Testing Strategy

### Unit Tests (30+ new)

1. **Argument Parsing** (10 tests):
   - Global options parsed correctly
   - Subcommand options parsed correctly
   - Invalid arguments rejected with clear errors
   - Help text displayed correctly

2. **Filtering** (8 tests):
   - Section prefix filtering
   - Rule ID glob patterns (exact, wildcard, multiple)
   - Question ID glob patterns
   - Empty filter results handled gracefully

3. **Verbose/Dry-Run** (5 tests):
   - Verbose logs LLM calls
   - Dry-run mocks API calls
   - Dry-run implies verbose
   - Mock responses handled correctly

4. **Cache Management** (5 tests):
   - `--clean-cache` deletes correct files
   - `--ignore-cache` skips read/write
   - Filtered cache cleaning (e.g., only 5.5.2)

5. **Integration** (2 tests):
   - Full `all` command runs successfully
   - Command chaining works (parse → rules → questions → validate)

### Manual Testing

- Run each command with `--help`
- Verify verbose output is readable
- Confirm dry-run doesn't make API calls
- Test filtering with various patterns
- Verify cache cleaning deletes correct files

---

## Risk Mitigation

**Risk**: Breaking existing workflows
**Mitigation**: Maintain backward compatibility, keep old `run_pipeline.py` behavior as default

**Risk**: Complex argparse configuration
**Mitigation**: Use subparsers cleanly, comprehensive testing

**Risk**: Filtering edge cases (empty results, invalid patterns)
**Mitigation**: Defensive programming, clear error messages

**Risk**: Verbose/dry-run mode adds complexity
**Mitigation**: Isolate in separate modules, test thoroughly

---

## Acceptance Criteria

Phase 5 is complete when:

- [ ] All 5 subcommands implemented and working
- [ ] Global options (`--verbose`, `--dry-run`, `--clean-cache`, `--ignore-cache`) functional
- [ ] Filtering works for sections, rules, and questions
- [ ] Rule IDs added to all extracted rules
- [ ] All 87 existing tests still pass
- [ ] 30+ new CLI tests pass (total: 117+ tests)
- [ ] README.md updated with CLI documentation
- [ ] Help text comprehensive and clear
- [ ] Manual testing completed for all workflows
- [ ] No regressions in existing functionality

---

## Estimated Effort

- **Stage 5A** (Subcommand Architecture): 3-4 hours
- **Stage 5B** (Rule IDs + Filtering): 2-3 hours
- **Stage 5C** (Verbose/Dry-Run): 2-3 hours
- **Stage 5D** (Cache Management): 1-2 hours
- **Stage 5E** (Testing + Docs): 3-4 hours

**Total**: 11-16 hours (2-3 work sessions)

---

## Dependencies

- **Prerequisites**: Phases 1-4 complete (✅)
- **Blocking**: None
- **Blocked By**: None

---

## Next Phase Preview

**Phase 6**: Export & Format Conversion
- CSV export using template format
- JSON export with metadata
- Coverage statistics report
- Integration tests for full pipeline
