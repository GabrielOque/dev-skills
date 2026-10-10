# {{PROJECT_NAME}} — backend

Django + DRF + PostgreSQL (psycopg 3), JWT via `djangorestframework-simplejwt`.
Read this before changing anything; it is the contract the rest of the code follows.

## Layout

```
config/          settings (100% env-driven), root urls, wsgi/asgi, CustomAuthConfig
common/          base layer every app imports — never imports an app at module level
  models.py        BaseModel (UUID pk, created_at, updated_at, archived)
  viewsets.py      SecureViewSet, SecureModelViewSet, OrganizationScopedMixin, UniqueConflictMixin
  decorators/      required_perms, required_any_perms, audit_action
  exceptions.py    error contract + ServiceError
  listing.py       raw-SQL listing plumbing (fetch_page, page_response, resolve_*)
  queries.py       build_where_clause
  tenancy.py       get_profile / get_organization(_id)
  services/        email
  testing.py       test factories
accounts/        DjangoUser (AUTH_USER_MODEL), ValidationCode, credential services
organizations/   Organization (the tenant) + organization/current/
users/           User (business profile), Role, Permission catalogue, fixture, commands
authentication/  /api/auth/: login, refresh, activation, password reset
audit/           AuditLog (written by @audit_action, no API)
```

**Domain app anatomy** — one Django app per business module, each model,
serializer and viewset in its own file, aggregated by the package `__init__.py`:

```
<app>/
  models/        <model>.py …, __init__.py re-exports
  serializers/   <resource>.py …
  views/         <resource>.py …
  services/      business rules (or services.py while small)
  tests/         test_<topic>.py
  admin.py  apps.py  urls.py  choices.py (TextChoices)  migrations/
```

Infrastructure apps (`common`, `accounts`, `authentication`, `audit`) stay flat.

## Rules

1. **Every model inherits `common.models.BaseModel`.** UUID pk; nothing is deleted —
   `destroy` archives, `restore` reactivates.
2. **Every action is gated.** `SecureViewSet`/`SecureModelViewSet` refuse undecorated
   actions (`MISSING_PERMS_DECORATOR`). Decorator order on a mutation:
   `@audit_action` → `@required_perms([...])` → `@transaction.atomic` → `@action(...)`.
3. **Permissions, never roles.** Code checks codenames (`module.resource.action`),
   never role names. Roles are per-organization bundles the customer composes.
   Django `Group` / `auth.Permission` are not used (Group is unregistered from the admin).
4. **New codename = fixture row in the same change.** Add it with
   `python manage.py add_permission <codename> "<description>"` (writes the row to
   `users/fixtures/permissions_catalog.json` with its deterministic uuid5 pk — never
   invent pks), apply with `sync_permissions`, and mirror it in the frontend
   `libs/permission-codenames.ts`. Renames go through `RENAMES` in
   `sync_permissions`. A codename missing from the fixture can never be held.
   Action vocabulary: `view / create / edit / deactivate` (+ domain verbs such as
   `approve`, `export`) — never `delete`, nothing is deleted.
5. **Tenant isolation.** Every tenant-owned model has `organization` (or reaches it
   through a parent). Viewsets use `OrganizationScopedMixin`; the organization is
   stamped from the caller (`get_organization(request)`), never read from the payload.
6. **Error contract.** Every error is `{"code": "SCREAMING_SNAKE_CASE", "message":
   "English", "detail"?}`. Codes are stable (renaming one breaks the frontend); reuse
   before inventing. Business rules raise `common.exceptions.ServiceError`. The
   frontend maps codes to UI copy in `libs/api-messages.ts` — add new codes there too.
7. **The backend speaks English** (code, comments, API messages). Exceptions: email
   subjects/templates, permission descriptions and `TextChoices` labels — a person
   reads them directly.
8. **Listings.** Raw SQL with `COUNT(*) OVER()` through `common/listing.py`; envelope
   `{"results", "page", "page_size", "total_pages", "total_rows"}`; filters via
   `build_where_clause` (values are parameters, columns come from code). Plain ORM is
   fine for small, unpaginated lists.
9. **Thin views, services hold the rules.** Views parse, call a service, serialize.
10. **Settings come from the environment.** New setting = read it with the `env*`
    helpers in `config/settings.py` and document it in `.env.example`, same change.

## Migrations

- One migration per logical change: `makemigrations <app> --name <what_changed>`.
- Never edit or delete a migration that has run anywhere shared; add a new one.
- Data migrations use `RunPython` with a reverse function (or `noop` when safe).
- Never remove a function or class a migration imports by path.
- CI runs `makemigrations --check`: a model change without its migration fails.
- `common/migrations/0001_postgres_extensions.py` enables `unaccent`; keep it first.

## Auth & sessions

- Login: `POST /api/auth/login/ {username: <email>, password}`. The email is normalized
  (trim + lowercase) and is the `username`.
- Access token 15 min, refresh token 3 days, rotated on every refresh
  (`JWT_ACCESS_TOKEN_MINUTES`, `JWT_REFRESH_TOKEN_DAYS`). The refresh re-validates the
  account, so deactivating a user or organization ends their session within one
  access-token lifetime.
- Login, refresh and `GET /api/me/` all return `{user, organization}`; `user.permissions`
  is the effective set (superuser = every permission).
- `must_change_password` → login answers `403 PASSWORD_CHANGE_REQUIRED` + `reset_code`.
- Activation and password-reset links use `ValidationCode` bound to a purpose; a code
  never works for another flow. Password-reset requests answer the same for unknown
  emails. Password policy: `accounts.services.password_policy_failures` (mirrored in
  the frontend `libs/validators.ts`).

## Commands

```bash
python manage.py test
python manage.py makemigrations --check --dry-run
python manage.py sync_permissions --dry-run
python manage.py check --deploy        # with production env vars
```
