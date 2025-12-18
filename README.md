# LOAC Benchmarks

Generate AI benchmarking questions from the DoD Law of War Manual with full provenance tracking.

## How It Works

The pipeline transforms legal documents into validated benchmark questions in 6 stages:

```
PDF → parse → rules → questions → validate → eval → score
```

1. **parse** — Extract text from PDF, preserving section hierarchy and footnote refs
   - In: `./section_5_5.pdf` → Out: `data/extracted/sections.json`

2. **rules** — GPT-4o identifies discrete legal rules (verbatim extraction)
   - In: `data/extracted/sections.json` → Out: `data/extracted/rules.json`

3. **questions** — Generate 4 question types per rule
   - In: `data/extracted/rules.json` → Out: `data/generated/questions.json`
   - Types: definitional, scenario-easy, scenario-hard, refusal

4. **validate** — LLM-based quality checks; export passing questions
   - In: `data/generated/questions.json` → Out: `data/validated/questions.json`, `data/validated/benchmark_questions.csv`

5. **eval** — Run target model through questions, collect responses
   - In: `data/validated/questions.json` → Out: `data/evaluation/eval_responses.json`

6. **score** — Deterministic scoring + analysis report
   - In: `data/evaluation/eval_responses.json` → Out: `data/evaluation/eval_scored.json`

Each question includes full provenance: source section, page numbers, verbatim rule text, and confidence scores.

## Quick Start

```bash
# Prerequisites: Python 3.9+, uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup
git clone <repo-url> && cd loac
uv sync
cp .env.example .env  # Add your OPENAI_API_KEY

# Run full pipeline
uv run python run_pipeline.py all --section 5.5

# Run tests
make test
```

## CLI Commands

```bash
run_pipeline <command> [options]

Commands:
  all        Run full pipeline (parse → rules → questions → validate)
  parse      Extract sections from PDF
  rules      Extract legal rules from sections (GPT-4o)
  questions  Generate questions from rules (4 per rule)
  validate   Validate questions and export to CSV
  eval       Evaluate target model on validated questions
  score      Score evaluation responses

Global Options:
  -v, --verbose      Show all LLM prompts/responses
  -d, --dry-run      Print prompts without API calls
  --ignore-cache     Fresh run, no cache
  --clean-cache      Delete cache for this command
```

### Examples

```bash
# Full pipeline (default: section 5.5)
uv run python run_pipeline.py all

# Process specific rule
uv run python run_pipeline.py questions --rule-id "5.5_r0"

# Evaluate with different model
uv run python run_pipeline.py eval --model gpt-4o-mini

# Debug: see prompts without calling API
uv run python run_pipeline.py -d questions --rule-id "5.5_r0"
```

## Output Files

```
./section_5_5.pdf                        # Input PDF (you provide this)
data/
├── extracted/
│   ├── sections.json                    # Parsed sections with hierarchy
│   └── rules.json                       # Extracted legal rules
├── generated/questions.json             # All generated questions (4 per rule)
├── validated/
│   ├── questions.json                   # Questions passing validation
│   └── benchmark_questions.csv          # Final benchmark format
└── evaluation/
    ├── eval_responses.json              # Model responses to questions
    └── eval_scored.json                 # Scored results + analysis
```

## Development

```bash
make help     # Show all targets
make test     # Lint + run tests
make format   # Auto-fix code style
make clean    # Remove data/cache (prompts first)
```

## License

MIT
