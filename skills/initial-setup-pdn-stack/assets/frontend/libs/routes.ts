/**
 * Route constants shared by `proxy.ts`, the auth actions and the pages, so a
 * path is written down exactly once.
 */

/** Where signed-out visitors land. The login form lives at the root. */
export const LOGIN_PATH = "/";

/** Where every signed-in user lands. There is no per-role landing page. */
export const HOME_PATH = "/home";

/** Reachable without a session. A route also covers everything below it. */
export const PUBLIC_ROUTES = [LOGIN_PATH, "/activate-account", "/reset-password"] as const;

export const isPublicRoute = (pathname: string) =>
  PUBLIC_ROUTES.some(
    (route) => pathname === route || (route !== "/" && pathname.startsWith(`${route}/`)),
  );

export const resetPasswordPath = (code: string) => `/reset-password/${encodeURIComponent(code)}`;
