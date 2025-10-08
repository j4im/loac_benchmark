# LOAC QA Pipeline

Automated question generation from the DoD Law of War Manual for AI benchmarking.

## Setup

**Prerequisites:** Python 3.9+, [uv](https://github.com/astral-sh/uv)

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone <repo-url>
cd loac
uv sync

# Configure API key
cp .env.example .env
# Edit .env: add OPENAI_API_KEY=your_key_here

# Verify
uv run pytest tests/
```

## Usage

**Current Status:** Phase 1 Complete - PDF parsing implemented

```bash
# Run the pipeline (Phase 1 only for now)
python run_pipeline.py --parse-only

# Or use directly in Python
uv run python -c "
from src.pipeline.parse import parse_document
import json
sections = parse_document('data/raw/section_5_5.pdf')
with open('data/extracted/section_5_5.json', 'w') as f:
    json.dump(sections, f, indent=2)
"
```

**Coming Soon:**
- Rule extraction (GPT-4o)
- Question generation (definitional, scenario, refusal)
- Validation & export
- Evaluation runner with AI-as-a-judge scoring

## Project Structure

```
loac/
├── src/           # Pipeline modules
├── tests/         # Unit tests
├── data/          # Input/output data
├── cache/         # API response cache
└── output/        # Final exports
```

## Development

```bash
uv run pytest              # Run tests
uv add package-name        # Add dependency
uv add --dev package-name  # Add dev dependency
```
