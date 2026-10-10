@AGENTS.md

# {{PROJECT_NAME}} — frontend

Next.js App Router + React + TypeScript + Redux Toolkit (+ redux-persist) + axios.
Talks to the Django backend (JWT). Read this before adding code.

`AGENTS.md` (written by create-next-app / `next dev`) is imported above: this Next.js version may
differ from what you remember — check `node_modules/next/dist/docs/` before using an API.

## Layout

```
app/                 routes only — thin `page.tsx` files that render a page component
  (app)/             route group: every authenticated screen; its layout mounts SessionSync
  reset-password/[code]/  activate-account/[code]/   public pages behind emailed links
  page.tsx           login (public)
page_components/     one folder per feature/screen: <feature>/<name>.tsx + index.ts
components/          reusable UI shared by features, grouped by kind (auth/, …) + index.ts
actions/             HTTP: api-client (authenticated) + auth/* (public flows, session)
redux/               store, typed hooks, slices/
libs/                pure helpers & constants: config, routes, cookies, jwt, validators,
                     api-messages, permissions, permission-codenames
hooks/               reusable hooks (usePermissions, …)
types/               shared TypeScript types, one file per domain
contexts/            React contexts, when one is needed
proxy.ts             route guard (Next.js 16+; `middleware.ts` on older versions)
```

**Aliases** (tsconfig): `@/a` actions · `@/c` components · `@/ctx` contexts · `@/h` hooks ·
`@/l` libs · `@/pc` page_components · `@/r` redux · `@/t` types. Every folder exports
through an `index.ts` barrel; import from the barrel (`@/c/auth`), not from deep files.

**Naming**: files and folders in kebab-case; components in PascalCase; hooks `use-*.ts`
exporting `useX`; one component per file.

## Rules

1. **Pages are thin.** `app/**/page.tsx` sets metadata and renders one component from
   `page_components/<feature>`. Logic lives in the page component; reusable pieces
   graduate to `components/`.
2. **Containers decide, presentational components receive.** The container fetches,
   holds state and computes permissions; presentational children take props
   (`canEdit`, `onSave`) and never fetch.
3. **HTTP only through `actions/`.** Authenticated calls use `apiClient`
   (`@/a/api-client`); never call `fetch`/`axios` with tokens by hand.
4. **Never render the backend's `message`.** Map `code` → copy in `libs/api-messages.ts`
   (`translateApiError(error, fallback)`; `getApiCode(error)` for control flow). New
   backend codes are added there in the same change.
5. **Permissions, not roles.** `usePermissions()` / `<Can>` with constants from
   `libs/permission-codenames.ts` (mirror of the backend fixture). Hide denied controls,
   don't disable them. This is UI honesty — the backend authorizes.
6. **Redux holds the session profile only** (`auth.user`, `auth.organization`). Use the
   typed hooks from `@/r/hooks`. Reducers stay pure; side effects live in actions.
7. **Design is a separate decision.** The base pages are unstyled skeletons. The UI kit,
   styling approach and visual language are chosen by the project — don't introduce them
   implicitly.

## Session

- Tokens live in cookies (`accessToken`, `refreshToken`) so `proxy.ts` can route before
  rendering; the profile is persisted in Redux (`redux-persist`, key `{{PROJECT_SLUG}}`).
- Access token ~15 min, refresh token ~3 days, rotated on every refresh. **The session
  lives as long as the refresh token**; an expired access token is normal.
- `apiClient` refreshes proactively before expiry with a single-flight promise; a failed
  refresh or any 401 calls `logout()`.
- `SessionSync` (in `app/(app)/layout.tsx`) refreshes once on mount so the profile and
  permissions are current before the shell paints.
- `logout()` (`@/a`) clears cookies, resets + purges the store and hard-navigates to `/`.
- Public routes are listed in `libs/routes.ts` (`PUBLIC_ROUTES`); add new ones there.

## Password flows

- Forgot password: login → "¿Olvidaste tu contraseña?" → `requestPasswordReset` (same
  answer for unknown emails) → email → `/reset-password/[code]` → verify once → set a
  password meeting `getPasswordRequirements` → backend returns a session → `/home`.
- Invitation: `/activate-account/[code]` — same steps plus first/last name.
- Forced change: login answers `PASSWORD_CHANGE_REQUIRED` with `reset_code` → redirect to
  `/reset-password/{reset_code}`.
- The password policy in `libs/validators.ts` mirrors the backend's
  `accounts.services.PASSWORD_RULES`; change both together.
