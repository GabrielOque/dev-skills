/**
 * Runtime configuration, read once from `NEXT_PUBLIC_*` variables.
 *
 * Those values are inlined at build time, so a missing one cannot be fixed at
 * runtime — it is reported as early as possible instead of every request
 * silently 404-ing against the frontend's own origin.
 */
const BACKEND_URL = (process.env.NEXT_PUBLIC_BACKEND_URL ?? "").replace(/\/+$/, "");

export const IS_BACKEND_CONFIGURED = BACKEND_URL.length > 0;

export const MISSING_BACKEND_CONFIG_MESSAGE =
  "NEXT_PUBLIC_BACKEND_URL is not set. Copy .env.example to .env.local and restart the dev server.";

if (!IS_BACKEND_CONFIGURED && typeof window !== "undefined") {
  console.error(`[config] ${MISSING_BACKEND_CONFIG_MESSAGE}`);
}

/** Every API path is built from here. Note the trailing slash Django expects. */
export const API_URL = `${BACKEND_URL}/api/`;

/** Guard for the calls that use bare axios instead of `apiClient`. */
export const assertBackendConfigured = () => {
  if (!IS_BACKEND_CONFIGURED) throw new Error(MISSING_BACKEND_CONFIG_MESSAGE);
};
