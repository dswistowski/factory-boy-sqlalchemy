# Repository Guidelines

## Project Structure & Module Organization

- `src/fbsa/`: Library code.
  - `factory.py`: Async factory binding and metaclass integration.
  - `pytest.py`: Pytest plugin exposing `sqlalchemy_async_factory`.
  - `types.py`, `__init__.py`: Public types and exports.
- `tests/`: Example and integration tests (`test_example_orders.py`, `conftest.py`).
- Top level: `README.md`, `pyproject.toml`, `Makefile`, `uv.lock`.

## Build, Test, and Development Commands

- `make lint`: Ruff format check + lint.
- `make typecheck`: Mypy type checking (SQLAlchemy mypy plugin enabled).
- `make check-all`: Runs lint + typecheck.
- `make format`: Auto-format and autofix lint issues with Ruff.
- `uv run pytest -q`: Run the test suite.

Examples:

```bash
uv run pytest -q
make check-all
```

## Coding Style & Naming Conventions

- Python 3.12+. Use 4-space indentation, UTF‑8, Unix EOLs.
- Follow PEP 8; modules/functions `snake_case`, classes `CamelCase`.
- Type hints required; mypy is strict (`disallow_untyped_defs`, etc.).
- Linting/formatting via Ruff; do not commit lint errors.
- Keep changes minimal and focused; mirror existing patterns.

## Testing Guidelines

- Framework: `pytest` with `pytest-asyncio` (asyncio mode auto).
- Enable plugin: `pytest_plugins = "fbsa.pytest"` (or run with `-p fbsa.pytest`).
- Write tests under `tests/` named `test_*.py`; use `@pytest.mark.asyncio` for async tests when useful.
- Prefer realistic SQLAlchemy models; use `async_session` fixture.
- For DBs, set `POSTGRES_DB_DSN` or `MYSQL_DB_DSN` to skip Testcontainers.

## Commit & Pull Request Guidelines

- Commits: short, imperative subject (<= 72 chars), concise body.
  - Example: `fix(pytest): cache bound factories per session`
- PRs: clear description, rationale, and scope; link issues; include tests and docs updates (e.g., README) when behavior changes.
- CI hygiene: run `make check-all` and `uv run pytest` locally before opening PRs.
- Small, focused PRs are preferred; include illustrative examples when adding features.

