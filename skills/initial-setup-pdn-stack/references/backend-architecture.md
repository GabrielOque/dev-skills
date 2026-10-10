# Backend architecture

How the Django repository is organized and why. The templates in
`assets/backend/` already implement all of this; read this file when you extend
the backend or need to explain a decision.

## Contents
- [Repository layout](#repository-layout)
- [App anatomy](#app-anatomy)
- [Layering and dependency direction](#layering-and-dependency-direction)
- [Models](#models)
- [Settings and environments](#settings-and-environments)
- [Migrations](#migrations)
- [Admin](#admin)
- [Services](#services)
- [Tests](#tests)

## Repository layout

```
config/            the Django project: settings.py, urls.py, wsgi/asgi, apps.py
common/            base layer — every app imports it, it imports no app at module level
accounts/          login identity (DjangoUser = AUTH_USER_MODEL), ValidationCode
organizations/     the tenant (Organization) + organization/current/ API
users/             business profile (User), Role, Permission catalogue + fixture + commands
authentication/    /api/auth/: login, refresh, activation, password reset (no models)
audit/             AuditLog, written by @audit_action (no API)
<domain apps>/     one per business module, added from the user's context
manage.py  requirements.txt  .env.example  .python-version  .github/workflows/ci.yml
README.md  CLAUDE.md
```

The project package is `config/` (not the project name) so every generated
repository looks the same and settings are always `config.settings`.

## App anatomy

**One Django app per business module.** A module is a coherent area of the
product the user describes (billing, scheduling, projects…) — not a table.
Domain apps use packages, one class per file, aggregated by `__init__.py`:

```
<app>/
  __init__.py
  apps.py
  admin.py            one ModelAdmin per model, inheriting common.admin.BaseModelAdmin
  urls.py             SimpleRouter; included from config/urls.py under "api/"
  choices.py          TextChoices of the app (stored values are language-neutral codes)
  models/
    __init__.py       from .invoice import Invoice … ; __all__ = [...]
    invoice.py
    invoice_line.py
  serializers/
    __init__.py
    invoice.py
  views/
    __init__.py
    invoice.py
  services/           business rules (start with services.py; split when it grows)
  tests/
    __init__.py
    test_invoices.py
  migrations/
  management/commands/   only when the app needs commands
```

Infrastructure apps (`common`, `accounts`, `authentication`, `audit`) are small
and stay flat (`models.py`, `views.py`…). Match whatever an app already does
before adding to it.

Naming: app labels plural and snake_case (`organizations`, `purchase_orders`);
models singular PascalCase; `db_table` set explicitly in singular snake_case
(`db_table = "invoice_line"`); URL prefixes plural kebab-case
(`router.register(r"invoice-lines", …)`).

## Layering and dependency direction

```
common  <-  accounts  <-  organizations  <-  users  <-  authentication
   ^                                           ^
   +-------------- domain apps ----------------+
```

- `common` never imports another project app at module level. When it needs a
  model it resolves it at call time: `apps.get_model("users", "Permission")`.
- Domain apps may import `common`, `organizations`, `users` and each other only
  in one direction — if two apps need each other, one of them owns the shared
  piece or the dependency goes through a service function.
- Cross-app foreign keys use string references (`"organizations.Organization"`).

## Models

- **Every model inherits `common.models.BaseModel`**: UUID pk, `created_at`,
  `updated_at`, `archived`. Never auto-increment ids in URLs.
- **Nothing is deleted.** `archived=True` is the deletion; the API calls it
  "deactivate". Hard deletes only for data that never had meaning on its own
  (expired codes, sessions).
- Tenant-owned models have `organization = models.ForeignKey("organizations.Organization", …)`
  or reach it through a parent (see access-control.md, tenant isolation).
- Every field has `verbose_name`; non-obvious ones have `help_text`.
- Uniqueness inside a tenant is a `UniqueConstraint(fields=["organization", "name"], name="<table>_unique_<what>")`,
  never `unique=True` on a tenant-scoped field.
- Choices: `TextChoices` with language-neutral stored values
  (`ACTIVE = "ACTIVE", "Activo"`): labels can be reworded without a data
  migration; the API sends the value, the frontend owns the label.
- Derived values (a type's capabilities, a status computed from two columns)
  are computed, not stored, unless there is a measured reason.
- Business numbering (`INV-000123`) uses a per-organization sequence row locked
  with `select_for_update()`, and the formatted number is stored as text on the
  document.
- File fields use a callable `upload_to` that prefixes the environment and the
  organization (`f"{settings.ENV}/organization_{self.organization_id}/invoices/{filename}"`),
  so environments never mix files in a shared bucket.

## Settings and environments

`config/settings.py` is a single module, 100% environment-driven:

- `.env` is loaded with `override=False` (platform variables win).
- Helpers `env`, `env_bool`, `env_int`, `env_list` treat an empty value as
  unset, so `.env.example` can list every key.
- `ENV` ∈ `local | test | production` switches infrastructure only (secure
  cookies, static storage, local defaults) — **never business behaviour**.
- `SECRET_KEY` is mandatory outside `local`; the app refuses to start without it.
- Database: `DATABASE_URL` (platforms) or discrete `DB_*` (local).
- Storage: S3-compatible bucket when `AWS_STORAGE_BUCKET_NAME` is set, local
  disk otherwise. Static files: WhiteNoise outside `local`.
- Email: console backend locally, SMTP (or a provider backend) elsewhere.

**Adding a setting** = read it with an `env*` helper with a safe default + add
it to `.env.example` with a comment, in the same change. A setting read in code
but missing from `.env.example` is a bug.

Do not split settings into `base/local/production` modules: one module plus
environment variables keeps every environment running the same code path.

## Migrations

- Generate per app with a descriptive name:
  `python manage.py makemigrations <app> --name <what_changed>` (the first one
  of each app is `--name initial`).
- Commit migrations with the model change that produced them. CI runs
  `makemigrations --check --dry-run`.
- Never edit, squash or delete a migration that ran in a shared environment;
  write a new one.
- Data migrations: `RunPython(forwards, backwards)`; use
  `apps.get_model(...)` inside, never import models directly. Use
  `migrations.RunPython.noop` as the reverse only when undoing is truly safe.
- Never delete a function or class that a migration references by import path
  (defaults, `upload_to` callables); leave it with a comment.
- `common/migrations/0001_postgres_extensions.py` creates `unaccent` and must
  run first. Add other extensions (`pg_trgm`, `btree_gin`) as new migrations in
  `common`.
- Changing a column that has data: add new → backfill (data migration) →
  switch code → remove old, across separate deploys when the table is large.

## Admin

- Every model is registered; admins inherit `common.admin.BaseModelAdmin`
  (adds `archived`/`created_at` filters and a collapsed "System control"
  fieldset).
- Define `list_display`, `search_fields`, `list_filter` and grouped `fieldsets`.
- Django `Group` is unregistered; the `DjangoUser` admin hides `groups` and
  `user_permissions`. Access is managed on `users.User` and `users.Role`.
- Audit and credential models are read-only in the admin.

## Services

Views are thin: parse the request (serializer), call a service, serialize the
result. Services:

- hold business rules and multi-model writes, wrapped in `@transaction.atomic`;
- receive explicit arguments (`organization`, validated data), never `request`;
- raise `common.exceptions.ServiceError(code, message, status)` for business
  refusals;
- send emails or call external systems **after** the transaction commits
  (call them after the service returns, or use `transaction.on_commit`).

## Tests

- Django `TestCase` + DRF `APIClient`, against PostgreSQL (raw SQL and
  `unaccent` need it). Build data with `common/testing.py`
  (`make_organization`, `make_user(..., permissions=[...])`, `authenticated_client`).
- Every new endpoint gets at least: allowed with its permission, `403` without
  it, and tenant isolation (another organization's record is `404`).
- Test business rules at the service level, contracts (status + `code`) at the
  API level.
- `cache.clear()` in `setUp` for tests that hit throttled endpoints.
