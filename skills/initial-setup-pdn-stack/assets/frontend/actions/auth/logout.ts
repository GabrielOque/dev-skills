import { clearSessionCookies } from "@/l/cookies";
import { LOGIN_PATH } from "@/l/routes";
import { persistor, store, USER_LOGOUT } from "@/r/store";

let loggingOut = false;

/**
 * Ends the session from anywhere: drops the cookies, resets and purges the
 * persisted store, and hard-navigates to the login page.
 *
 * The navigation is a full page load on purpose — it discards every in-memory
 * cache along with the store, which a client-side `router.push` would keep.
 * Safe to call several times (concurrent 401s): only the first one acts.
 *
 * Sessions are stateless JWTs, so there is no backend call: the refresh token
 * simply stops being presented.
 */
export const logout = async () => {
  if (loggingOut) return;
  loggingOut = true;
  clearSessionCookies();
  store.dispatch({ type: USER_LOGOUT });
  await persistor.purge();
  if (typeof window !== "undefined") window.location.replace(LOGIN_PATH);
};
