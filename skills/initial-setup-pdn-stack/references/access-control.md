# Access control: users, roles and permissions

The project replaces Django's `Group` / `auth.Permission` with its own models so
that each organization builds **its own roles** from a catalogue of permissions
the application defines. Read this before adding a gated endpoint, a new
permission, or anything that touches users or roles.

## Contents
- [The model](#the-model)
- [Why not Django groups and permissions](#why-not-django-groups-and-permissions)
- [The permission catalogue (fixture)](#the-permission-catalogue-fixture)
- [Effective permissions](#effective-permissions)
- [Gating endpoints](#gating-endpoints)
- [Tenant isolation](#tenant-isolation)
- [Hiding Django's machinery in the admin](#hiding-djangos-machinery-in-the-admin)
- [Frontend mirror](#frontend-mirror)
- [Checklist: adding a permission](#checklist-adding-a-permission)

## The model

```
accounts.DjangoUser (AUTH_USER_MODEL)      login identity: username(=email), password, is_active,
        | 1:1  related_name="profile"      is_superuser, must_change_password
users.User (db_table user_profile)         business profile: organization, roles, permissions
        |-- organization -> organizations.Organization
        |-- roles        -> users.Role (M2M)          inherited permissions
        |-- permissions  -> users.Permission (M2M)    additional permissions
users.Role                                 organization + name (unique per org) + permissions (M2M)
users.Permission                           name (codename, unique) + description — global catalogue
```

- **Identity vs profile.** Auth concerns stay on `DjangoUser`; everything the
  business cares about (organization, access, domain fields such as a document
  number or phone) goes on `users.User`. Don't blur the two.
- **Login is by email**: `username` always holds the normalized (trimmed,
  lowercased) email.
- A login without a profile (`createsuperuser`) can use `/admin` only; the API
  answers `403 NO_PROFILE` and login answers `401 NO_PROFILE`.
- **Single company or SaaS — same code.** A single-company product has one
  `Organization` row; a multi-tenant one has many.

## Why not Django groups and permissions

- `auth_group.name` is globally unique: two organizations could never both have
  an "Administrator" role. `Role` is scoped per organization.
- `auth.Permission` is generated per model (`add_/change_/delete_/view_<model>`).
  The catalogue describes product **actions** (`billing.invoices.void`), which
  is what an administrator understands and what endpoints need.
- Their tables live in a package you don't own. The `auth_*` tables still exist
  (the admin site uses them), but nothing in the project's authorization reads
  them.

## The permission catalogue (fixture)

**`users/fixtures/permissions_catalog.json` is the only source of truth.**

- Codename shape `<module>.<resource>.<action>` (2–4 lowercase snake_case
  segments): `access.users.view`, `billing.invoices.void`. The module is the
  first segment and is derived, never stored.
- Action vocabulary: `view`, `create`, `edit`, `deactivate`, plus domain verbs
  when an action is distinct (`approve`, `void`, `export`). **Never `delete`** —
  nothing is deleted. One codename per distinct capability; don't create
  codenames that nothing checks.
- `description` is written in the UI language: it is what the person composing
  a role reads.
- **Deterministic pks**: `pk = uuid5(PERMISSION_NAMESPACE, codename)`
  (`users.models.permission_pk`). `loaddata` is idempotent and every
  environment has the same ids. Never invent pks: use
  `python manage.py add_permission <codename> "<description>" …` (in the
  project) or `scripts/permission_rows.py` (in this skill).
- `python manage.py sync_permissions` validates the fixture, upserts it,
  applies `RENAMES` (moves role/user assignments from an old codename to its
  replacements) and **deletes permissions not in the fixture**. Run it on every
  deploy after `migrate`. `--dry-run` shows the diff.
- Renaming a codename = new row. Add `"old": ["new"]` to `RENAMES` in
  `sync_permissions.py` in the same change, keep it until every environment ran.

Base catalogue shipped by the template:

| Codename | Gates |
| --- | --- |
| `access.users.view/create/edit/deactivate` | `users/` (edit also gates resend-invitation and send-password-reset) |
| `access.roles.view/create/edit/deactivate` | `roles/` |
| `access.permissions.view` | `permissions/` (also readable with roles.create/edit, users.edit) |
| `organization.settings.view/edit` | `organization/current/` |

`bootstrap_organization` creates the first organization, an all-permissions
role and its owner; from there the owner composes roles in the application.

## Effective permissions

`common.decorators.get_effective_permission_codenames(django_user)`:

- union of the permissions of every **non-archived** role + the user's direct
  permissions; archived permissions grant nothing from any source;
- roles never subtract;
- a superuser holds **every** permission (so the frontend, which renders from
  the list, shows everything to the one account allowed to see everything);
- returned in the session payload as `user.permissions` (login, refresh, `GET me/`).

## Gating endpoints

```python
@audit_action
@required_perms(["billing.invoices.void"])
@transaction.atomic
@action(detail=True, methods=["post"])
def void(self, request, pk=None): ...
```

- `@required_perms([...])` — AND; `@required_any_perms([...])` — OR (read
  catalogues several screens need); `@required_perms("None")` — any signed-in
  user (own profile, own settings).
- `SecureViewSet` / `SecureModelViewSet` raise `MISSING_PERMS_DECORATOR` for any
  undecorated action, superusers included: forgetting a gate fails loudly.
- `destroy` / `restore` of `SecureModelViewSet` archive/reactivate and must be
  overridden with their own decorators and delegate to `super()`.
- A denial is `403 {"code": "PERMISSION_DENIED"}`; the missing codenames go to
  the log, never to the client.
- **Never check role names in code.** Roles are data the customer edits.
- Several actions may share one codename (resend invitation rides on
  `access.users.edit`); document it on the frontend constant.

## Tenant isolation

Permissions say **what**; tenancy says **whose**.

- Resource viewsets mix in `OrganizationScopedMixin`: `get_queryset()` filters by
  the caller's organization, so a foreign record is `404` (existence is not
  disclosed). Child models set `organization_lookup = "parent__organization_id"`.
- The organization is stamped from the caller (`get_organization(request)` /
  `perform_create`), never accepted from the payload — serializers don't expose
  an `organization` field.
- Any id received in a payload (roles, related records) is resolved **inside
  the caller's organization** (`users.services.resolve_roles` is the pattern).
- Raw SQL listings always include `{"type": "equal", "value": get_organization_id(request), "fields": ["x.organization_id"]}`.
- Fixed MRO: `class XViewSet(UniqueConflictMixin, OrganizationScopedMixin, SecureModelViewSet)`.

## Hiding Django's machinery in the admin

- `users/admin.py`: `admin.site.unregister(Group)`.
- `accounts/admin.py`: `DjangoUserAdmin` without `groups` / `user_permissions`
  (`filter_horizontal = ()`).
- `config/apps.py`: `CustomAuthConfig` replaces `django.contrib.auth` in
  `INSTALLED_APPS` only to relabel its admin section.
- The `Permission` admin makes `name` read-only on existing rows (the fixture
  owns codenames); `UserAdmin` only offers roles of the user's organization.

## Frontend mirror

- `libs/permission-codenames.ts` mirrors the fixture as nested constants
  (`PERMISSIONS.access.users.create`). Never type codename strings in components.
- `usePermissions()` (`can`, `canAll`, `canAny`) and `<Can permission|all|any>`
  decide what the UI **offers**; hide denied controls, don't disable them.
- A screen's navigation entry carries the codenames that gate it; denied
  entries are removed, and a group whose children are all denied disappears.
- It is UI honesty, not security: the backend re-checks every request.

## Checklist: adding a permission

1. `python manage.py add_permission <module>.<resource>.<action> "<description>"`.
2. Gate the endpoint(s) with `@required_perms([...])`.
3. If it replaces an old codename, add the rename to `RENAMES`.
4. `python manage.py sync_permissions --dry-run`, then without `--dry-run`.
5. Mirror it in the frontend `libs/permission-codenames.ts` and gate the UI.
6. Tests: allowed with it, `403` without it.
