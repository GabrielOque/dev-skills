# Authentication and sessions (backend + frontend)

End-to-end design of sign-in, the JWT session, silent refresh and the password
flows. Both halves are already implemented by the templates; read this when
changing anything about sessions, adding a sign-in method, or debugging a
logout loop.

## Contents
- [Endpoints](#endpoints)
- [Token lifetimes and rotation](#token-lifetimes-and-rotation)
- [What every session response contains](#what-every-session-response-contains)
- [Frontend session architecture](#frontend-session-architecture)
- [Password and account flows](#password-and-account-flows)
- [Security rules](#security-rules)
- [Adding a sign-in method](#adding-a-sign-in-method)

## Endpoints

All under `/api/auth/`, public, rate-limited (`AUTH_THROTTLE_RATE`, per IP):

| Endpoint | Body | Answer |
| --- | --- | --- |
| `POST login/` | `username` (email), `password` | session · `401 INVALID_CREDENTIALS` · `403 PASSWORD_CHANGE_REQUIRED` + `reset_code` |
| `POST refresh/` | `refresh` | session with a **rotated** refresh · `401 TOKEN_INVALID / USER_OR_ORGANIZATION_ARCHIVED / INACTIVE_USER` |
| `POST activation/verify/` | `code` | `{email, first_name, last_name}` · `INVALID_CODE / EXPIRED_CODE / ALREADY_ACTIVATED` |
| `POST activation/confirm/` | `code, first_name, last_name, password` | session · `WEAK_PASSWORD` |
| `POST password-reset/request/` | `email` | always `200 PASSWORD_RESET_REQUESTED` |
| `POST password-reset/verify/` | `code` | `{email, …}` · `INVALID_CODE / EXPIRED_CODE / INACTIVE_USER` |
| `POST password-reset/confirm/` | `code, password` | session · `WEAK_PASSWORD` |

Authenticated: `GET me/` (session payload), `PATCH me/profile/`,
`POST me/password/ {current_password, new_password}`.

## Token lifetimes and rotation

| Setting | Default | Env |
| --- | --- | --- |
| Access token | 15 minutes | `JWT_ACCESS_TOKEN_MINUTES` |
| Refresh token | 3 days | `JWT_REFRESH_TOKEN_DAYS` |
| Rotation | on every refresh | `ROTATE_REFRESH_TOKENS = True` |

- **The session lives as long as the refresh token.** An expired access token is
  normal; the frontend mints a new one silently before it expires.
- Rotation makes the session *sliding*: an active user stays signed in; a user
  idle for longer than the refresh lifetime is signed out.
- The refresh serializer **re-validates the account** (exists, active, profile
  and organization not archived). Deactivating someone ends their session within
  one access-token lifetime.
- No token blacklist by default (stateless). If the project needs immediate
  revocation, enable `rest_framework_simplejwt.token_blacklist` with
  `BLACKLIST_AFTER_ROTATION = True` and add a logout endpoint that blacklists the
  refresh token — a deliberate, documented change.

## What every session response contains

Login, refresh, activation confirm, password-reset confirm:

```json
{
  "access": "…", "refresh": "…",
  "user": {
    "id": "<profile uuid>", "django_user_id": "<login uuid>",
    "email": "…", "first_name": "…", "last_name": "…", "full_name": "…",
    "roles": ["Administrator"],
    "permissions": ["access.users.view", "…"],
    "is_superuser": false, "must_change_password": false
  },
  "organization": {"id": "…", "name": "…", "slug": "…"}
}
```

Because the refresh returns the profile too, every refresh also updates the
name, roles and permissions the frontend persisted. `GET me/` returns
`{user, organization}` without tokens.

## Frontend session architecture

```
login/activation/reset ──► applySession(data) ──► cookies: accessToken, refreshToken
                                              └─► redux auth slice: user, organization (persisted)
proxy.ts (server, every navigation) ── reads refreshToken cookie ── routes
(app)/layout.tsx ── <SessionSync> ── ensureFreshSession() once on mount
apiClient (axios) ── request interceptor: token about to expire? → single-flight refreshSession()
                  └─ response interceptor: 401 → logout()
logout() ── clear cookies → USER_LOGOUT (store reset) → persistor.purge() → full reload to "/"
```

- **Cookies, not localStorage, for tokens**: `proxy.ts` must read them on the
  server before rendering. Cookie lifetime = refresh token `exp` + 1 day, so the
  proxy can still see an expired token and end the session deliberately. Cookies
  are `SameSite=Lax`, `Secure` on HTTPS.
- **Redux holds only the profile** (`auth.user`, `auth.organization`), persisted
  with `redux-persist` through a storage wrapper that is a no-op during SSR.
- **Reducers are pure.** Cookies, purging and navigation live in
  `actions/auth/*`.
- **`proxy.ts`** (Next.js 16+; `middleware.ts` before): no live refresh token on a
  protected route → redirect to `/` and drop cookies; live session on `/` →
  redirect to `/home`; public routes come from `libs/routes.ts`.
- **`apiClient`** refreshes *before* expiry (`EXPIRATION_THRESHOLD_MS`) instead of
  waiting for a 401, and shares one in-flight refresh promise among concurrent
  requests. Public flows use bare `axios` (no token to attach).
- **`SessionSync`** blocks the authenticated shell until the session is fresh:
  the shell needs current permissions to decide what to show.
- **`logout()`** is idempotent (concurrent 401s) and performs a full page load to
  discard every in-memory cache.

## Password and account flows

### Forgot password
1. Login → "¿Olvidaste tu contraseña?" (the typed email is carried over).
2. `password-reset/request/` — same answer whether or not the email exists; the
   UI shows the same neutral confirmation.
3. Email with `{FRONTEND_URL}/reset-password/{code}` (valid
   `VALIDATION_CODE_HOURS`, single use; issuing a new link invalidates the old).
4. Page verifies the code **once** (a ref guards React's double effect in dev):
   - dead link codes (`INVALID_CODE`, `EXPIRED_CODE`, `INACTIVE_USER`) → terminal
     "invalid link" state with a way back to login;
   - anything else (rate limit, network, 5xx) → retryable state. Never call a
     valid link invalid because the network failed.
5. New password with a live checklist (`getPasswordRequirements`, mirror of the
   backend policy); submit disabled until it passes.
6. `password-reset/confirm/` returns a session → `applySession` → `/home`.
   A link that died meanwhile switches to the invalid state.

### Invitation (account activation)
Admin creates the user (`POST users/`) → inactive login without a usable
password + activation email → `/activate-account/{code}` → verify (pre-fills the
name) → name + password → `activation/confirm/` returns a session → `/home`.
`resend-invitation` issues a fresh link and kills the previous one.

### Forced password change
An administrator sets a temporary password (`must_change_password = True`, also
what `bootstrap_organization` does without `--password`). The **password**
login answers `403 PASSWORD_CHANGE_REQUIRED` with a fresh `reset_code` and no
tokens; the login page redirects to `/reset-password/{reset_code}`. Setting the
password clears the flag. Refresh and other flows ignore the flag.

### Changing my password
`POST me/password/` requires the current password whenever the account has a
usable one (a stolen session must not be enough to take the account), rejects
reusing it, and applies the policy.

## Security rules

- Codes are `secrets.token_urlsafe(32)`, bound to a **purpose**: a reset code is
  never accepted by activation and vice versa; one active code per user and
  purpose; deleted on use.
- Enumeration: reset requests answer identically for unknown emails; login
  answers `INVALID_CREDENTIALS` for wrong password, unknown or inactive account.
- Password policy enforced by the backend (`password_policy_failures`: length,
  upper, lower, digit, special + Django validators) and mirrored in the frontend.
- Auditing redacts passwords, tokens and codes (`common/decorators/audit.py`).
- Behind a load balancer set `NUM_PROXIES` so throttling sees real client IPs.

## Adding a sign-in method

Every method ends the same way: validate the account with
`authentication.services.validate_login_user(django_user)` and return
`issue_session(django_user)`. Proxy, `apiClient` and Redux need no changes.

- **Email one-time code (OTP)**: add a `LOGIN_OTP` value to
  `ValidationCode.Purpose`; `otp/request/` issues a 6-digit code with
  `secrets.randbelow` and a short TTL (≈1–5 min), answers the same for unknown
  emails; `otp/verify/` looks the code up **by email and purpose** (never by
  code alone), compares with `secrets.compare_digest`, caps attempts in the cache
  (burn the code after N failures, `429 TOO_MANY_ATTEMPTS`), deletes it on
  success, then `issue_session`.
- **External identity provider (Google, Microsoft…)**: verify the provider's ID
  token server-side; store the link in a `SocialAccount(django_user, provider,
  provider_uid)` table keyed by the provider's stable subject id, unique per
  (provider, uid) and (provider, user). Match by email **only once** to link an
  already-provisioned account and only if the provider marks the email verified;
  never auto-create users (they need an organization) and never re-link a user
  to a second identity automatically. The feature switches off when its client
  id env var is empty.
