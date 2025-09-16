# Contributing

Thanks for your interest in improving PoGo Analyzer! This guide explains how to set up your environment, submit changes, and keep the tooling consistent.

## Development setup

1. Fork and clone the repository.
2. Create a virtual environment and install optional tooling:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install pandas openpyxl  # optional, enables Excel exports during testing
   ```

3. Install any additional tooling you prefer (e.g., `black`, `ruff`, `mypy`) for local linting. The repository does not currently enforce a specific formatter, but PEP 8 style is encouraged.

## Making changes

- **Tests first** – update or add unit tests alongside your changes. Run `python -m unittest` before opening a pull request.
- **Document behavior** – keep README, API docs, and docstrings in sync with the code. Include runnable examples whenever possible.
- **Coding style** – favour clear naming, small functions, and descriptive docstrings. Avoid adding pandas-only constructs inside the core package so scripts remain usable without optional dependencies.
- **Data updates** – when editing `pogo_analyzer/raid_entries.py`, make sure notes explain any special move requirements or mega considerations so readers understand the resulting score.

## Pull requests

1. Create a descriptive branch name (e.g., `feature/add-shadow-support`).
2. Keep commits focused and include concise commit messages describing _what_ changed and _why_.
3. Link to related issues or discussions in the pull request description when applicable.
4. Confirm the automated checks pass. Include the command output in your PR description if CI is unavailable.
5. Request review from maintainers or other contributors.

## Reporting issues

When filing a bug report or feature request, include:

- Current behavior and the expected result
- Steps to reproduce (commands, input files, etc.)
- Environment details (OS, Python version, whether pandas is installed)
- Screenshots or logs if helpful

We appreciate thoughtful, actionable feedback—thanks again for contributing!
