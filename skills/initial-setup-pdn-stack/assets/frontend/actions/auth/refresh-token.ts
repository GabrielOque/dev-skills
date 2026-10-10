import axios from "axios";

import { API_URL, assertBackendConfigured } from "@/l/config";
import { ACCESS_TOKEN_COOKIE, getCookie, REFRESH_TOKEN_COOKIE } from "@/l/cookies";
import { isTokenExpired } from "@/l/jwt";
import { store } from "@/r/store";
import type { AuthResponse } from "@/t/auth";

import { applySession } from "./session";

/**
 * Exchanges the refresh token for a new access token, stores the rotated
 * refresh token and the fresh profile, and returns the new access token.
 *
 * Every refresh doubles as a session update: the backend re-validates the
 * account and sends the current `user` (permissions included) and
 * `organization`.
 *
 * Uses bare axios: `apiClient` would try to refresh to send this very request.
 *
 * @throws when there is no live refresh token or the backend refuses it.
 */
export const refreshSession = async (): Promise<string> => {
  assertBackendConfigured();
  const refreshToken = getCookie(REFRESH_TOKEN_COOKIE);
  if (!refreshToken || isTokenExpired(refreshToken)) {
    throw new Error("The session has expired.");
  }

  const { data } = await axios.post<AuthResponse>(`${API_URL}auth/refresh/`, { refresh: refreshToken });
  applySession(data, refreshToken);
  return data.access;
};

/**
 * Brings the persisted session up to date when the authenticated shell mounts.
 *
 * `proxy.ts` already let the request through on the strength of the refresh
 * token, but the access token may be stale and the persisted profile may be
 * out of date. Refreshing mints a fresh access token *and* re-reads `user` and
 * `organization`, so the UI never renders yesterday's name or permissions.
 *
 * @returns true when there is a usable session.
 */
export const ensureFreshSession = async (): Promise<boolean> => {
  const refreshToken = getCookie(REFRESH_TOKEN_COOKIE);
  if (!refreshToken || isTokenExpired(refreshToken)) return false;

  const hasProfile = store.getState().auth.user !== null;
  if (hasProfile && !isTokenExpired(getCookie(ACCESS_TOKEN_COOKIE))) {
    // Fresh enough: `apiClient` refreshes on demand as the token ages.
    return true;
  }

  try {
    await refreshSession();
    return true;
  } catch {
    return false;
  }
};
