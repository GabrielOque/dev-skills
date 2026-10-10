import axios from "axios";

import { API_URL, assertBackendConfigured } from "@/l/config";
import { normalizeEmail } from "@/l/validators";
import type { AuthResponse, CodeOwner } from "@/t/auth";

import { applySession } from "./session";

/**
 * Asks for a reset link. Resolves the same way whether or not the email is
 * registered (the backend never reveals which accounts exist), so a resolved
 * promise means "we asked", not "the email was sent".
 */
export const requestPasswordReset = async (email: string): Promise<void> => {
  assertBackendConfigured();
  await axios.post(`${API_URL}auth/password-reset/request/`, { email: normalizeEmail(email) });
};

/**
 * Checks the code carried by the emailed link. Rejects with the backend's
 * `code`: `INVALID_CODE`, `EXPIRED_CODE` or `INACTIVE_USER`.
 */
export const verifyPasswordResetCode = async (code: string): Promise<CodeOwner> => {
  assertBackendConfigured();
  const { data } = await axios.post<CodeOwner>(`${API_URL}auth/password-reset/verify/`, { code });
  return data;
};

/**
 * Sets the new password and signs the person in: the backend answers with a
 * full session, so they land on the app without typing the password again.
 * Rejects with `WEAK_PASSWORD`, `INVALID_CODE` or `EXPIRED_CODE`.
 */
export const confirmPasswordReset = async (code: string, password: string): Promise<AuthResponse> => {
  assertBackendConfigured();
  const { data } = await axios.post<AuthResponse>(`${API_URL}auth/password-reset/confirm/`, {
    code,
    password,
  });
  applySession(data);
  return data;
};
