# 🤝 Contributing Guide

**TL;DR:** We welcome contributions! Ensure your code adheres to our `ruff` linting standards and utilizes the custom `i18n` engine for all user-facing text.

## Local Development Workflow
1. Fork the repository.
2. Clone your fork and create a branch.
3. Install dependencies via `pip install -r requirements.txt`.
4. Run the bot using a local MongoDB instance. Use the `--debug` flag (`python -m app --debug`) to isolate database operations into a `_debug` collection.

## Code Style
The project uses `ruff` as defined in `pyproject.toml`:
- **Line Length**: 120 characters.
- **Target Version**: Python 3.12.
- **Ignores**: `E501` (long lines are common in message templates), `E731` (lambdas allowed), and `E402`.

Please run `ruff check .` before submitting a Pull Request.

## Writing Handlers
- **Do not hardcode strings**. Always use the `i18n` engine from `app.i18n`.
- Keep business logic inside `app/services/` and leave `app/handlers/` strictly for request parsing and response formatting.
