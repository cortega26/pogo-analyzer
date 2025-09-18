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

3. Install the tooling used by the repository:

   ```bash
   pip install black ruff
   ```

   Formatting and linting are enforced via the shared `pyproject.toml` configuration.

## Making changes

- **Tests first** – update or add unit tests alongside your changes. Run `python -m unittest` before opening a pull request.
- **Document behavior** – keep README, API docs, and docstrings in sync with the code. Include runnable examples whenever possible.
- **Coding style** – follow the naming conventions documented in `docs/api.md`. Run `ruff check` and `black .` to verify formatting before submitting.
- **Data updates** – when editing `pogo_analyzer/data/raid_entries.py`, make sure notes explain any special move requirements or mega considerations so readers understand the resulting score.

## Release process

1. Make sure the `CHANGELOG.md` "Unreleased" section accurately reflects the upcoming release. Move its entries into a new version section dated for the release.
2. Bump the version number in `pyproject.toml`. The package exposes the `pogo_analyzer.__version__` attribute via this value, so no other files need manual edits.
3. Run `ruff check`, `black . --check`, and `python -m unittest` to verify the codebase is clean and the tests pass.
4. Commit the changes, create an annotated tag such as `git tag -a vX.Y.Z -m "Release vX.Y.Z"`, and push both the branch and tag.
5. Build the distribution artifacts with `python -m build` and upload them using `twine upload dist/*` once you're ready to publish on PyPI.

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
