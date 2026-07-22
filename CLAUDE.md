# django-clickify — Claude Notes

## Environment

This is a **Django library** (no `manage.py`). Tests and migrations can run via Poetry or a local `.venv`.

## Installing dependencies

**Option A — venv (preferred, no Poetry required):**

```bash
make setup
```

Creates `.venv/`, installs the package and all dev dependencies.

**Option B — Poetry:**

Poetry installs to `~/.local/bin`. If `poetry` is not found, add it to PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
poetry install
```

## Running tests

```bash
make test
```

Automatically detects Poetry, `.venv`, or system Python. Django settings come from `tests/settings.py`. The in-memory SQLite database runs all migrations on every test run — a migration failure shows up here before any test executes.

To run a specific test file:

```bash
.venv/bin/python -m pytest tests/test_utm.py
# or with Poetry:
poetry run pytest tests/test_utm.py
```

## Linting

```bash
.venv/bin/ruff check clickify/ tests/
# or:
make check
```

## Generating migrations

There is no `manage.py`. Use `django-admin` with the test settings:

```bash
.venv/bin/django-admin makemigrations clickify --settings=tests.settings
# or with Poetry:
poetry run django-admin makemigrations clickify --settings=tests.settings
```

## Branches

- `main` — upstream origin (romjanxr/django-clickify)
- `beta` — base branch for local customisations; PRs merge here not main
- Feature branches prefixed `yyyy-mm-` off `beta`
