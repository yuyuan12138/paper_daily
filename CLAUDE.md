# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

This project uses `uv` for Python package management. The virtual environment is located in `.venv/` and uses Python 3.13.

### Common Commands

- **Install dependencies**: `uv pip install <package>`
- **Run Python**: `uv run python <script>` or `python <script>` (with venv activated)
- **Activate venv**: `source .venv/bin/activate`

## Rules

1. Before writing any code, describe your approach and wait for approval. If requirements are unclear, be sure to ask clarifying questions before writing any code.
2. When a bug is discovered, first write a test that can reproduce the bug, then keep fixing it until the test passes. If it hasn't passed after five attempts, report the bug details.
3. Every time I correct you, modify, delete, or add rules in the CLAUDE.md file to avoid similar situations from occurring.
4. If a task involves changes to more than 3 files, stop immediately. Decompose it into smaller sub-tasks first.
5. Call existing skills whenever possible.
6. Once the code is written, identify potential edge cases or bugs and provide test cases to verify them.
