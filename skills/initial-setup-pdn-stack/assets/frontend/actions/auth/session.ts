import { clearSessionCookies, getCookie, REFRESH_TOKEN_COOKIE, writeSessionCookies } from "@/l/cookies";
import { setSession } from "@/r/slices";
import { store } from "@/r/store";
import type { AuthResponse } from "@/t/auth";

/**
 * Seeds the session from any response that carries one (login, refresh,
 * activation, password reset): tokens to cookies, profile to the store.
 *
 * `refresh` is optional in the payload; when absent the current refresh token
 * is kept instead of blanking the cookie.
 */
export const applySession = (data: AuthResponse, currentRefreshToken?: string | null) => {
  const refreshToken = data.refresh ?? currentRefreshToken ?? getCookie(REFRESH_TOKEN_COOKIE);
  if (!refreshToken) {
    clearSessionCookies();
    throw new Error("The response carried no refresh token and none is stored.");
  }
  writeSessionCookies(data.access, refreshToken);
  store.dispatch(setSession({ user: data.user, organization: data.organization }));
};
