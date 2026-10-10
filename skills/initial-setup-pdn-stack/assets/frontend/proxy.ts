import { NextResponse, type NextRequest } from "next/server";

import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE, SESSION_COOKIES } from "@/l/cookies";
import { isTokenExpired } from "@/l/jwt";
import { HOME_PATH, isPublicRoute, LOGIN_PATH } from "@/l/routes";

/**
 * Route guard that runs before every render (Next.js 16 renamed `middleware`
 * to `proxy`; on Next.js 15 or older name this file `middleware.ts` and export
 * `middleware`).
 *
 * The session lives as long as the **refresh** token: the access token is
 * short-lived and the API client mints a new one on demand, so an expired
 * access token is normal and must never sign anyone out.
 *
 * This is routing, not authorization — the backend checks every request.
 */
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value;
  const hasSession = Boolean(refreshToken) && !isTokenExpired(refreshToken);

  // Signed in and on the login screen: straight to the app.
  if (hasSession && pathname === LOGIN_PATH) {
    return NextResponse.redirect(new URL(HOME_PATH, request.url));
  }

  // Signed out (or the refresh token died) on a protected route.
  if (!hasSession && !isPublicRoute(pathname)) {
    const response = NextResponse.redirect(new URL(LOGIN_PATH, request.url));
    SESSION_COOKIES.forEach((name) => response.cookies.delete(name));
    return response;
  }

  // A dead session lingering on a public page: drop it so nothing reuses it.
  if (!hasSession && request.cookies.has(ACCESS_TOKEN_COOKIE)) {
    const response = NextResponse.next();
    SESSION_COOKIES.forEach((name) => response.cookies.delete(name));
    return response;
  }

  return NextResponse.next();
}

export const config = {
  // Everything except Next internals, API routes and files with an extension.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
