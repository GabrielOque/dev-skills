import { getTokenExpiration } from "./jwt";

/**
 * Session cookies. The tokens live in cookies — not in the persisted store —
 * so `proxy.ts` can read them on the server before anything renders.
 */
export const ACCESS_TOKEN_COOKIE = "accessToken";
export const REFRESH_TOKEN_COOKIE = "refreshToken";
export const SESSION_COOKIES = [ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE] as const;

const DAY_SECONDS = 24 * 60 * 60;

/** Reads a cookie by name. Always null on the server. */
export const getCookie = (name: string): string | null => {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((entry) => entry.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
};

export const setCookie = (name: string, value: string, maxAgeSeconds: number) => {
  if (typeof document === "undefined") return;
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=${Math.max(0, Math.floor(maxAgeSeconds))}; Path=/; SameSite=Lax${secure}`;
};

export const deleteCookie = (name: string) => {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax`;
};

/**
 * Writes both tokens. The cookies outlive the refresh token by a day, so the
 * proxy can still read an expired refresh token and end the session on
 * purpose instead of the cookie silently vanishing first. The lifetime comes
 * from the token itself — the backend's configuration is never duplicated.
 */
export const writeSessionCookies = (accessToken: string, refreshToken: string) => {
  const refreshExpiration = getTokenExpiration(refreshToken) ?? Date.now();
  const maxAge = (refreshExpiration - Date.now()) / 1000 + DAY_SECONDS;
  setCookie(ACCESS_TOKEN_COOKIE, accessToken, maxAge);
  setCookie(REFRESH_TOKEN_COOKIE, refreshToken, maxAge);
};

export const clearSessionCookies = () => SESSION_COOKIES.forEach(deleteCookie);
