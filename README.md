
# django-lit-urls

Django URLS delivered as string literal functions in Javascript

## Install

From source: `poetry install` from this directory
From pypi: `pip install django-lit-urls`

## Tests and Linting

The following tests should not raise anything:

```bash
poetry run black --check .
poetry run flake8 .
poetry run isort .
poetry run python -m mypy django_lit_urls/
```
