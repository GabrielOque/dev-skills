import axios from "axios";

import { API_URL, assertBackendConfigured } from "@/l/config";
import { normalizeEmail } from "@/l/validators";
import type { AuthResponse } from "@/t/auth";

import { applySession } from "./session";

/**
 * Signs in with email + password and seeds the session.
 *
 * The backend authenticates on Django's `username`, which always holds the
 * normalized email, so the typed email is sent as `username`.
 *
 * Rejects with the backend's error: `INVALID_CREDENTIALS`, or
 * `PASSWORD_CHANGE_REQUIRED` (403, with a `reset_code`) when an administrator
 * set a temporary password — the caller sends the person to
 * `/reset-password/{reset_code}`.
 *
 * Bare axios: there is no session yet for `apiClient` to attach.
 */
export const login = async (email: string, password: string): Promise<AuthResponse> => {
  assertBackendConfigured();
  const { data } = await axios.post<AuthResponse>(`${API_URL}auth/login/`, {
    username: normalizeEmail(email),
    password,
  });
  applySession(data);
  return data;
};
