# {{PROJECT_NAME}} — backend

Django + Django REST Framework + PostgreSQL, JWT authentication.

## Getting started

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   ·   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # then fill in the database values
createdb {{PROJECT_DB}}              # or create it from your PostgreSQL client
python manage.py migrate
python manage.py sync_permissions
python manage.py bootstrap_organization --organization "My company" \
    --email you@example.com --first-name You --last-name Surname
python manage.py runserver
```

`bootstrap_organization` prints a temporary password when `--password` is
omitted; the first sign-in asks to replace it.

## Everyday commands

| Command | What it does |
| --- | --- |
| `python manage.py makemigrations <app> --name <what_changed>` | One migration per logical change, named after it |
| `python manage.py migrate` | Apply migrations |
| `python manage.py add_permission <codename> "<description>"` | Add a codename to the catalogue fixture (deterministic pk) |
| `python manage.py sync_permissions [--dry-run]` | Make the permission table match `users/fixtures/permissions_catalog.json` |
| `python manage.py test` | Run the test suite (needs PostgreSQL) |
| `python manage.py check --deploy` | Production settings checklist |

## Deploying

Release step on every deploy, in this order:

```bash
python manage.py migrate --noinput
python manage.py sync_permissions
python manage.py collectstatic --noinput
```

Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.
Health check: `GET /health/` (no database access).

Conventions, architecture and the API contract are in [`CLAUDE.md`](./CLAUDE.md).
