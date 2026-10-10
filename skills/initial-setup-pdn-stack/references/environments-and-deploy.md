# Environments, configuration and deploy

## Contents
- [Environments](#environments)
- [Rules for variables](#rules-for-variables)
- [Backend variables](#backend-variables)
- [Frontend variables](#frontend-variables)
- [Release steps](#release-steps)
- [Hosting notes](#hosting-notes)
- [CI](#ci)
- [Go-live checklist](#go-live-checklist)

## Environments

| `ENV` | Where | Branch (suggested) | Backend URL | Frontend URL |
| --- | --- | --- | --- | --- |
| `local` | developer machine | any | `http://localhost:8000` | `http://localhost:3000` |
| `test` | shared staging | `test` | platform URL | platform URL |
| `production` | live | `main` | custom domain | custom domain |

Each deployed environment has its **own database, bucket prefix, secrets and
URLs**. `ENV` only switches infrastructure (secure cookies, static files); the
same code runs everywhere.

## Rules for variables

- Everything that differs between environments is an environment variable.
  Nothing environment-specific is hardcoded, and no secret is ever committed.
- `.env.example` (committed) lists **every** variable the code reads, with a
  comment and a safe local value. Real values live in `.env` / `.env.local`
  (git-ignored) or in the platform's settings.
- A new variable is added to the code and to `.env.example` in the same change,
  and to every deployed environment before the deploy that needs it.
- Empty means unset (the backend helpers fall back to the default).
- Frontend `NEXT_PUBLIC_*` values are inlined **at build time**: changing one
  needs a rebuild of that environment. Never put a secret in a `NEXT_PUBLIC_*`
  variable — it ships to every browser.

## Backend variables

| Variable | Local | Deployed |
| --- | --- | --- |
| `ENV` | `local` | `test` / `production` |
| `DEBUG` | `True` | `False` (never True) |
| `SECRET_KEY` | empty (dev key) | required, unique per environment |
| `JWT_SIGNING_KEY` | empty | optional, rotate independently of SECRET_KEY |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | API domain(s) |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | frontend origin(s) |
| `CSRF_TRUSTED_ORIGINS` | (= CORS) | frontend + `https://<api-domain>` (admin) |
| `FRONTEND_URL` | `http://localhost:3000` | frontend URL (email links) |
| `DATABASE_URL` / `DB_*` | `DB_*` | `DATABASE_URL` injected by the platform |
| `DB_SSL_REQUIRE` | `False` | `True` (unless a private network refuses SSL) |
| `JWT_ACCESS_TOKEN_MINUTES` / `JWT_REFRESH_TOKEN_DAYS` | 15 / 3 | 15 / 3 |
| `VALIDATION_CODE_HOURS` | 24 | 24 |
| `AUTH_THROTTLE_RATE`, `NUM_PROXIES` | default, empty | default, `1` behind a load balancer |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | console backend | SMTP / provider credentials |
| `AWS_*` | empty (local disk) | bucket + credentials (+ endpoint for S3-compatible) |
| `TIME_ZONE`, `LOG_LEVEL`, `PROJECT_NAME` | | |

Generate secrets with `python -c "import secrets; print(secrets.token_urlsafe(50))"`.

## Frontend variables

| Variable | Local | Deployed |
| --- | --- | --- |
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | API origin of that environment (no `/api`, no trailing slash) |

The app logs a loud error when it is missing instead of silently calling its
own origin.

## Release steps

Backend, on every deploy (release/pre-deploy command), in order:

```bash
python manage.py migrate --noinput
python manage.py sync_permissions
python manage.py collectstatic --noinput
```

Start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 60 --access-logfile - --error-logfile -`.
Health check: `GET /health/` (never touches the database, so a database blip
does not restart the container).

First deploy of an environment, once: `python manage.py bootstrap_organization …`
(prints a temporary password when `--password` is omitted).

Frontend: the platform runs `pnpm install --frozen-lockfile && pnpm build`, then
`pnpm start` (or its native Next.js runtime). Build each environment from its
branch with its own variables.

## Hosting notes

Deploy targets are the user's decision; only add platform files once chosen.

- **Railway / Render / Fly / Heroku-like (backend)**: Python buildpack or
  Dockerfile; `DATABASE_URL` from the managed PostgreSQL; set the release
  command above; health check `/health/`; `NUM_PROXIES=1`. The platform's
  public domain goes in `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- **Vercel / Netlify (frontend)**: one project per repository, an environment per
  branch, `NEXT_PUBLIC_BACKEND_URL` per environment; optionally ignore builds of
  branches other than `main`/`test`.
- **Docker**: one image per repository; the same release command as the
  container's pre-start step; never bake `.env` into the image.
- **PostgreSQL**: managed service with automatic backups; the role needs
  permission to create the `unaccent` extension on the first migrate.

## CI

Both templates ship `.github/workflows/ci.yml`:

- backend: PostgreSQL service → `check --fail-level WARNING` →
  `makemigrations --check --dry-run` → `migrate` + `sync_permissions --dry-run`
  → `test`;
- frontend: `pnpm install --frozen-lockfile` → `lint` → `tsc --noEmit` → `build`.

Protect `main` and `test`: changes arrive by pull request with CI green.

## Go-live checklist

- [ ] `DEBUG=False`, unique `SECRET_KEY`, `ENV=production`.
- [ ] `python manage.py check --deploy` reviewed with production variables.
- [ ] `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `FRONTEND_URL` point at the real domains (HTTPS).
- [ ] Email provider configured and a reset email received end to end.
- [ ] Bucket private; uploads reachable through signed URLs only.
- [ ] Release command runs `migrate` and `sync_permissions`.
- [ ] Database backups enabled and a restore tested.
- [ ] First organization bootstrapped; temporary password changed.
