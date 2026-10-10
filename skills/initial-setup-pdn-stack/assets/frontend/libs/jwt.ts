/**
 * Minimal JWT helpers shared by the axios client and `proxy.ts`.
 *
 * Decoding only — the signature is never checked here. Tokens are read to
 * decide *when to refresh* and *where to route*; the backend remains the only
 * authority on whether a request is authorized.
 *
 * Runs in the proxy as well as the browser, so it sticks to `atob` and avoids
 * Node built-ins.
 */

interface JwtPayload {
  exp?: number;
}

/** Refresh this long before a token actually expires. */
export const EXPIRATION_THRESHOLD_MS = 10 * 1000;

/** Expiration in milliseconds, or null when the token is absent or unreadable. */
export const getTokenExpiration = (token: string | null | undefined): number | null => {
  if (!token) return null;
  try {
    const [, payload] = token.split(".");
    if (!payload) return null;
    // JWT uses base64url without padding; atob expects padded base64.
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const decoded = JSON.parse(atob(padded)) as JwtPayload;
    return decoded.exp ? decoded.exp * 1000 : null;
  } catch {
    return null;
  }
};

/**
 * True when the token is missing, unreadable, or within `threshold` of
 * expiring. Unreadable counts as expired, so callers fail closed.
 */
export const isTokenExpired = (
  token: string | null | undefined,
  threshold = EXPIRATION_THRESHOLD_MS,
): boolean => {
  const expiration = getTokenExpiration(token);
  return expiration === null || expiration - Date.now() <= threshold;
};
