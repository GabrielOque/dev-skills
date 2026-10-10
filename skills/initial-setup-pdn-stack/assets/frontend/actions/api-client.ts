import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { API_URL, assertBackendConfigured } from "@/l/config";
import { ACCESS_TOKEN_COOKIE, getCookie } from "@/l/cookies";
import { isTokenExpired } from "@/l/jwt";
import type { ApiErrorBody } from "@/t/api";

import { logout } from "./auth/logout";
import { refreshSession } from "./auth/refresh-token";

/**
 * The HTTP client for every authenticated call. Public endpoints (login,
 * activation, password reset) use bare axios in `actions/auth/*`.
 *
 * - Attaches `Authorization: Bearer <access>`.
 * - Refreshes the access token *before* it expires (proactive), so requests
 *   don't bounce with 401s every 15 minutes.
 * - Single-flight refresh: concurrent requests await the same promise, so a
 *   burst of calls triggers exactly one refresh.
 * - A failed refresh or any 401 ends the session (`logout`).
 *
 * Usage: `const { data } = await apiClient.get<PaginatedResponse<Role>>("roles/", { params })`.
 */
export const apiClient = axios.create({ baseURL: API_URL });

let refreshInFlight: Promise<string> | null = null;

const freshAccessToken = (): Promise<string> => {
  refreshInFlight ??= refreshSession()
    .catch((error: unknown) => {
      void logout();
      throw error;
    })
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
};

apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  assertBackendConfigured();
  const accessToken = getCookie(ACCESS_TOKEN_COOKIE);
  const token = accessToken && !isTokenExpired(accessToken) ? accessToken : await freshAccessToken();
  config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorBody>) => {
    // The backend refused the credentials themselves (deactivated account,
    // revoked profile…): the session is over, whatever the token says.
    if (error.response?.status === 401) void logout();
    return Promise.reject(error);
  },
);

export default apiClient;
