# django-clickify — Claude Notes

## Environment

This is a **Django library** (no `manage.py`). Tests and migrations run via Poetry.

Poetry installs to `~/.local/bin`. If `poetry` is not found, add it to PATH first:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

To make this permanent in the container:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

## Installing dependencies

```bash
poetry install
```

Creates a virtualenv under `~/.cache/pypoetry/virtualenvs/` and installs all dependencies from `poetry.lock`. Only needed once per environment (or after adding new dependencies to `pyproject.toml`).

## Running tests

```bash
poetry run pytest
```

Runs the full suite with coverage. Django settings come from `tests/settings.py` (configured via `DJANGO_SETTINGS_MODULE` in `pyproject.toml`). The in-memory SQLite database runs all migrations on every test run — a migration failure shows up here before any test executes.

To run a specific test file:

```bash
poetry run pytest tests/test_utm.py
```

## Generating migrations

There is no `manage.py`. Use `django-admin` through Poetry with the test settings:

```bash
poetry run django-admin makemigrations clickify --settings=tests.settings
```

## Branches

- `main` — upstream origin (romjanxr/django-clickify)
- `beta` — base branch for local customisations; PRs merge here not main
- Feature branches prefixed `yyyy-mm-` off `beta`
