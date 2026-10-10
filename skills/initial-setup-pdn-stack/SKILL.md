---
name: initial-setup-pdn-stack
description: >-
  Bootstraps a production-grade project on the PDN stack — PostgreSQL, Django REST
  Framework and Next.js (App Router) — with the architecture already decided: one Django
  app per business module plus a shared `common` layer, env-driven settings for
  local/test/production, UUID models with soft delete, JWT sessions (15-min access,
  3-day rotating refresh), its own users/roles/permissions replacing Django groups
  (a permission catalogue fixture so each organization builds its own roles), audited
  mutations, and a Next.js frontend with cookie + Redux Toolkit session, route-guard
  proxy, auto-refreshing API client and complete password recovery/activation flows.
  Use when the user wants to start, scaffold or "montar" a new project, backend or
  frontend with Django and Next.js, asks for an initial setup ("setup inicial",
  "arrancar el proyecto"), or wants to add a module to a project built with it.
license: MIT
compatibility: Needs Python 3.12+, Node.js 20.9+, PostgreSQL 15+ and git. Written for Claude Code; works with any Agent Skills client that can run shell commands.
metadata:
  version: "1.0.0"
  summary: "Monta back (Django + DRF + PostgreSQL) y front (Next.js) con auth JWT, roles/permisos propios y estructura lista para crecer por módulos."
  category: "development"
  tags: "django,django-rest-framework,nextjs,postgresql,jwt,rbac,redux-toolkit,scaffolding"
---

# Initial setup — PDN stack (PostgreSQL · Django · Next.js)

You are setting up a new product on a fixed, proven architecture. The **structure and
practices are decided** (this skill); the **product, its names and its design are the
user's** (ask). Templates in `assets/` are tested code — copy them with the scaffold
script, don't rewrite them from memory.

## Ground rules

1. **Structure, not design.** Never choose a UI kit, CSS approach, colors, fonts or
   layout. Base pages are unstyled, semantic skeletons. If the user wants a design
   system, they name it.
2. **No borrowed names.** Every app, model, route and permission comes from the user's
   own domain language (translated to English identifiers). Names in this skill's
   examples (`billing`, `invoices`) are placeholders — never reuse them.
3. **Ask before modelling business.** Infrastructure ships now; domain modules are built
   only from what the user describes (phase 4).
4. **Code speaks English** (identifiers, comments, API messages with stable `code`s);
   UI copy, emails and permission descriptions use the user's UI language.
5. **Verify before claiming.** Each phase ends with its checks green. Report failures
   with their output.

## Workflow

Copy this checklist into your reply and keep it updated:

```
- [ ] 1. Discover: answers collected, plan confirmed
- [ ] 2. Backend: scaffolded, deps pinned, migrated, permissions synced, owner bootstrapped, tests green
- [ ] 3. Frontend: created, overlaid, deps installed, lint/tsc/build green
- [ ] 4. Domain modules from the user's context (repeat per module)
- [ ] 5. Verify end to end and hand off
```

### 1. Discover

Ask everything in **one** message; offer the defaults so the user can just confirm:

| Decision | Default | Used for |
| --- | --- | --- |
| Project name | — (required) | repo names, `PROJECT_NAME`, DB name |
| What the product does; first modules | — | phase 4 (not scaffolded yet) |
| Repository layout | two repos: `<slug>-back`, `<slug>-front` (siblings) | targets |
| Where to create them | next to the current directory | targets |
| UI language | `es` | `<html lang>`, UI copy, emails, permission descriptions |
| Time zone | the user's (e.g. `America/Bogota`) | `TIME_ZONE` |
| Single company or multi-tenant SaaS | single company (one organization row) | docs/bootstrap only — same code |
| Package manager (frontend) | pnpm | create-next-app flags |
| Styling decided now? | no — decide later | `--tailwind` only if they ask for it |
| First owner (org name, email, names) | — | `bootstrap_organization` |
| Deploy targets | decide later | add platform files only once chosen |

Restate the plan in 5–8 lines (what will be created, where) and wait for confirmation.

### 2. Backend

```bash
python <skill>/scripts/scaffold.py backend --target <dir>/<slug>-back \
    --project-name "<Name>" --time-zone <Area/City> --html-lang <lang>
cd <dir>/<slug>-back
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # Windows
# .venv/bin/python -m pip install -r requirements.txt       # macOS / Linux
python <skill>/scripts/pin_requirements.py .                # exact versions into requirements.txt
cp .env.example .env                                         # fill DB_* (ask for credentials if unknown)
createdb <slug_with_underscores>                             # or via the user's PostgreSQL client
python manage.py makemigrations accounts organizations users audit --name initial
python manage.py migrate
python manage.py sync_permissions
python manage.py bootstrap_organization --organization "<Org>" --email <owner email> \
    --first-name <First> --last-name <Last>                  # prints a temporary password
python manage.py check && python manage.py test
```

`<skill>` is this skill's directory (`${CLAUDE_SKILL_DIR}` in Claude Code). Use the
venv's python for every `manage.py` call. If PostgreSQL is not reachable, stop and ask —
do not switch to SQLite (raw SQL and `unaccent` need PostgreSQL).

Then set the permission catalogue's language: the base fixture ships English codenames
(`access.users.view`) with Spanish descriptions; if the UI language is not Spanish,
rewrite the `description`s in `users/fixtures/permissions_catalog.json` (codenames
stay) and the copy in `common/templates/emails/`.

### 3. Frontend

```bash
cd <dir>
npx create-next-app@latest <slug>-front --ts --app --eslint --no-src-dir \
    --import-alias "@/*" --use-pnpm --no-tailwind --no-react-compiler --no-agent-feedback --disable-git --yes
python <skill>/scripts/scaffold.py frontend --target <dir>/<slug>-front \
    --project-name "<Name>" --html-lang <lang>
cd <slug>-front
pnpm add @reduxjs/toolkit react-redux redux-persist axios
cp .env.example .env.local
pnpm lint && pnpm exec tsc --noEmit && pnpm build
```

Swap `--use-pnpm` for the chosen manager and `--no-tailwind` for `--tailwind` only if
the user asked for it. The overlay replaces `app/layout.tsx` and `app/page.tsx`, merges
the path aliases into `tsconfig.json`, un-ignores `.env.example`, removes the demo
assets, and keeps `AGENTS.md` (Next.js's own agent rules — read
`node_modules/next/dist/docs/` before using an API you are unsure about). On Next.js
≤ 15 rename `proxy.ts` to `middleware.ts` and its export to `middleware`.

### 4. Domain modules

For each part of the product the user describes, follow
[references/new-module-playbook.md](references/new-module-playbook.md): agree on models,
lifecycle and codenames first, then backend app → permissions → error codes →
migrations + tests → frontend feature. One module at a time, each ending green.

### 5. Verify and hand off

- Backend: `python manage.py check`, `makemigrations --check --dry-run`,
  `sync_permissions --dry-run`, `test`.
- Frontend: `lint`, `tsc --noEmit`, `build`.
- Run both (`runserver`, `pnpm dev`) and walk the flow: `/home` redirects to `/`, sign in
  with the owner's temporary password → forced to `/reset-password/<code>` → new
  password → `/home` shows the owner's name → logout.
- `git init` each repository and make the first commit only if the user wants it.
- Hand-off message: what was created and where, how to run it, the owner account, the
  open decisions (design system, hosting), and the next module to build.

## Architecture at a glance

- **Backend layout**: `config/` (env-driven settings) · `common/` (BaseModel, secure
  viewsets, permission/audit decorators, error contract, raw-SQL listing helpers) ·
  `accounts/` (login identity, UUID) · `organizations/` (tenant) · `users/` (profile,
  roles, permission catalogue) · `authentication/` · `audit/` · one app per business
  module with `models/ serializers/ views/ services/ tests/` packages.
- **Access**: own `Permission` catalogue (fixture, deterministic uuid5 pks,
  `sync_permissions`), per-organization `Role`s, effective permissions = active roles ∪
  direct grants; `@required_perms` on every action (enforced by the base viewsets);
  Django `Group` hidden; tenant isolation by queryset scoping.
- **API contract**: `{code, message, detail?}` errors with stable codes; English backend;
  `@audit_action` on mutations; soft delete; `{results, page, page_size, total_pages, total_rows}` listings.
- **Sessions**: 15-min access / 3-day rotating refresh, refresh re-validates the account
  and returns the profile; frontend keeps tokens in cookies (read by `proxy.ts`) and the
  profile in Redux (persisted); proactive single-flight refresh; `SessionSync`;
  idempotent `logout()`.
- **Frontend layout**: `app/` thin routes (`(app)` group for authenticated screens),
  `page_components/<feature>`, `components/`, `actions/`, `redux/`, `libs/`, `hooks/`,
  `types/`, barrels + aliases (`@/a @/c @/h @/l @/pc @/r @/t`).

## References — load only what the task needs

| File | Read when |
| --- | --- |
| [references/backend-architecture.md](references/backend-architecture.md) | creating or reshaping apps, models, settings, migrations, admin, services, tests |
| [references/access-control.md](references/access-control.md) | users, roles, permissions, gating endpoints, tenant isolation |
| [references/auth-and-sessions.md](references/auth-and-sessions.md) | login/refresh/logout, password recovery, activation, adding a sign-in method (OTP, Google…) |
| [references/api-conventions.md](references/api-conventions.md) | writing endpoints: errors, viewset recipe, decorator order, listings, selectors |
| [references/frontend-architecture.md](references/frontend-architecture.md) | frontend folders, pages, components, data access, permissions in the UI, navigation |
| [references/environments-and-deploy.md](references/environments-and-deploy.md) | `.env`, environments, release steps, hosting, CI, go-live |
| [references/new-module-playbook.md](references/new-module-playbook.md) | adding a business module end to end |

## Scripts

| Script | Purpose |
| --- | --- |
| `scripts/scaffold.py backend\|frontend` | copy templates, fill placeholders, restore dotfiles, merge tsconfig aliases |
| `scripts/pin_requirements.py <backend>` | pin requirements.txt to the versions installed in `.venv` |
| `scripts/permission_rows.py` | build / `--append` / `--check` permission fixture rows with deterministic pks |

All are standard-library Python; run them with `--help` for options.

## Common mistakes

- Checking a role name in code instead of a permission codename.
- Adding `@required_perms` with a codename that is not in the fixture (it can never be
  held) or inventing fixture pks by hand.
- Accepting `organization` (or a foreign id) from the payload instead of the caller.
- Rendering the backend's `message` in the UI instead of mapping its `code`.
- Signing users out on an expired *access* token (the session is the refresh token's).
- Calling a link "invalid" when verification failed for network or rate-limit reasons.
- Introducing a UI library or styles the user did not choose.
- Reading a new setting in code without adding it to `.env.example`.
