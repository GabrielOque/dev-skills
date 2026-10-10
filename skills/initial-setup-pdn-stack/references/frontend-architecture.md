# Frontend architecture

How the Next.js repository is organized. This is **structure and practice
only**: the UI kit, styling approach, colors, typography and layout are design
decisions the project makes separately — never introduce them implicitly.

## Contents
- [Folder layout](#folder-layout)
- [Aliases and barrels](#aliases-and-barrels)
- [Naming](#naming)
- [Routes and pages](#routes-and-pages)
- [Page components vs shared components](#page-components-vs-shared-components)
- [Data access](#data-access)
- [State](#state)
- [Permissions in the UI](#permissions-in-the-ui)
- [Navigation as data](#navigation-as-data)
- [Error copy](#error-copy)
- [Lint rules worth knowing](#lint-rules-worth-knowing)

## Folder layout

```
app/                    routing only
  layout.tsx            <html>, providers
  page.tsx              "/" — login (public)
  reset-password/[code]/page.tsx     public
  activate-account/[code]/page.tsx   public
  (app)/                route group (no URL segment) for every authenticated screen
    layout.tsx          <SessionSync> + the app shell
    home/page.tsx
    <module>/<resource>/page.tsx, [id]/page.tsx, new/page.tsx
page_components/        feature code, one folder per feature/screen
  <feature>/index.ts    barrel
  <feature>/<name>.tsx
components/             reusable pieces shared by several features, by kind
  auth/                 SessionSync, Can, PasswordRequirements
  providers.tsx         every client provider, composed once
actions/                HTTP: api-client.ts (authenticated) + auth/* (session & public flows)
redux/                  store.ts, hooks.ts, provider.tsx, slices/
libs/                   pure helpers & constants (no React): config, routes, cookies, jwt,
                        validators, api-messages, permissions, permission-codenames, formatters…
hooks/                  reusable hooks: use-permissions.ts, …
types/                  shared types, one file per domain (auth.ts, api.ts, invoice.ts…)
contexts/               React contexts, created when first needed
proxy.ts                route guard (middleware.ts on Next.js ≤ 15)
```

## Aliases and barrels

`tsconfig.json` paths (merged by `scripts/scaffold.py`):

| Alias | Folder | Bare barrel |
| --- | --- | --- |
| `@/a/*` | actions | `@/a` |
| `@/c/*` | components | — (import `@/c/<group>`) |
| `@/ctx/*` | contexts | — |
| `@/h/*` | hooks | `@/h` |
| `@/l/*` | libs | `@/l` |
| `@/pc/*` | page_components | — (import `@/pc/<feature>`) |
| `@/r/*` | redux | — |
| `@/t/*` | types | `@/t` |

Every folder exposes an `index.ts` barrel; consumers import from the barrel
(`import { Can } from "@/c/auth"`), not from deep files. Inside a folder, files
import siblings relatively (`./forgot-password-form`). Prefer the specific
barrel (`@/l/routes`) in files that `proxy.ts` or server code import, to avoid
pulling browser-only modules into the server bundle.

## Naming

- Files and folders: kebab-case (`reset-password-page.tsx`, `api-client.ts`).
- Components: PascalCase, one per file, default export + named re-export in the
  barrel. Hooks: `use-*.ts` exporting `useX`. Types: PascalCase interfaces.
- Route segments are English (`/settings/users`); visible copy is in the UI
  language.
- Detail routes take the record's UUID (`/invoices/[id]`); the readable number
  goes in the heading.

## Routes and pages

- `app/**/page.tsx` is thin: `metadata` + render one component from
  `page_components`. No data fetching or state there.
- Group related screens with route groups `(name)` when they share a layout
  (tabs, a section header) without changing the URL.
- Public routes are declared once in `libs/routes.ts` (`PUBLIC_ROUTES`); the
  proxy reads them. A new public page = add it there.
- Pages using `useSearchParams` (URL-driven tables/filters) are wrapped in
  `<Suspense>` with a skeleton fallback.

## Page components vs shared components

```
page_components/invoices/
  index.ts                 export { default as InvoicesPage } …
  invoices-page.tsx        container: fetches, holds state, computes permissions
  invoices-table.tsx       presentational: rows in, events out
  invoice-editor.tsx       container for create/edit
  invoice-form-fields.tsx  presentational
  filters.tsx
```

- **Containers decide, presentational components receive.** The container
  calls `usePermissions()` and passes booleans (`canEdit`, `canDeactivate`);
  presentational components never fetch and never ask for permissions.
- A piece used by two features moves to `components/<kind>/` with a barrel.
- Read-only mode: when the user may view but not edit, the editor renders the
  same form with fields disabled and only a "back" action — computed as
  `readOnly = isEdit && !canEdit`.

## Data access

- Authenticated calls: `apiClient` from `@/a` (`apiClient.get<PaginatedResponse<Invoice>>("invoices/", { params })`).
  It attaches the token, refreshes it before expiry and logs out on 401.
- Group a resource's calls in `actions/<resource>.ts` when more than one
  component uses them; otherwise a container may call `apiClient` directly.
- Listing params mirror the backend: `page`, `page_size`, `search`, `status[]`
  (axios serializes arrays as `status[]=a&status[]=b` by default).
- Keep table state (page, filters, search) in the URL search params so
  refreshing or sharing a link restores the view.
- Types for every payload live in `types/<domain>.ts` with the backend's field
  names (snake_case), re-exported from `types/index.ts`.

## State

- Redux holds the session profile only (`auth.user`, `auth.organization`). Add a
  slice only for state that is truly global and long-lived; screen state stays
  in components, URL state in the URL.
- Always the typed hooks `useAppSelector` / `useAppDispatch` from `@/r/hooks`.
- Reducers are pure; side effects (cookies, storage, navigation, HTTP) live in
  `actions/`.
- `components/providers.tsx` is the only place providers are composed.

## Permissions in the UI

```tsx
const { can } = usePermissions();
const canCreate = can(PERMISSIONS.billing.invoices.create);
…
{canCreate && <button onClick={openCreate}>Nueva factura</button>}
// or declaratively
<Can permission={PERMISSIONS.billing.invoices.void}>…</Can>
```

- Constants from `libs/permission-codenames.ts` only (mirror of the backend
  fixture); never typed strings.
- Hide denied controls, don't disable them. Mirror the backend's
  `@required_perms` mapping — don't invent your own.
- Not authorization: the backend re-checks every request.

## Navigation as data

When the project builds its shell, navigation is **one config array**
(`components/navigation/navigation-config.ts`): entries with `key`, `label`,
`url`, an icon component and the `permissions` that gate them (AND), at most one
level of children. Every surface (sidebar, mobile menu, command palette,
breadcrumbs) renders from it after one pruning pass:

- an entry whose permissions fail is **removed**, not disabled;
- a parent whose children are all removed disappears;
- an entry without `permissions` is visible to every signed-in user.

A route guard can reuse the same pruned tree: typing the URL of a screen the
user can't open redirects to `/home` instead of mounting a page whose requests
all answer 403. Adding a screen = adding one entry to the config.

## Error copy

```tsx
try { … } catch (error) {
  setError(translateApiError(error, "No pudimos guardar los cambios."));
  if (getApiCode(error) === "INVOICE_ALREADY_VOID") { … }   // control flow
}
```

`translateApiError` resolves: mapped `code` → network failure → fallback. Never
render `error.response.data.message`. New backend codes are mapped in
`libs/api-messages.ts` in the same change.

## Lint rules worth knowing

`eslint-config-next` 16 enables the React Compiler rules:

- don't call `setState` synchronously inside an effect to mirror props — derive
  during render, or set state in an async callback;
- don't read or write `ref.current` during render (only in effects/handlers);
- effects that must run once in development (verifying a single-use code) guard
  with a ref.
