#!/usr/bin/env python3
"""
LOAC QA Pipeline - Main orchestration script.

This is a thin wrapper around the CLI module.
For usage information, run: python run_pipeline.py --help
"""

import sys
from src.cli import main

if __name__ == "__main__":
    sys.exit(main())
