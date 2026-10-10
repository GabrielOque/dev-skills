import axios from "axios";

import { API_URL, assertBackendConfigured } from "@/l/config";
import type { AuthResponse, CodeOwner } from "@/t/auth";

import { applySession } from "./session";

/**
 * Checks the code carried by the invitation link. Rejects with the backend's
 * `code`: `INVALID_CODE`, `EXPIRED_CODE` or `ALREADY_ACTIVATED`.
 */
export const verifyActivationCode = async (code: string): Promise<CodeOwner> => {
  assertBackendConfigured();
  const { data } = await axios.post<CodeOwner>(`${API_URL}auth/activation/verify/`, { code });
  return data;
};

export interface ActivationInput {
  code: string;
  firstName: string;
  lastName: string;
  password: string;
}

/**
 * Completes the invitation — confirms the person's name, sets their password,
 * activates the account — and signs them in with the session the backend
 * returns. Rejects with `WEAK_PASSWORD`, `INVALID_CODE`, `EXPIRED_CODE` or
 * `ALREADY_ACTIVATED`.
 */
export const confirmActivation = async ({ code, firstName, lastName, password }: ActivationInput) => {
  assertBackendConfigured();
  const { data } = await axios.post<AuthResponse>(`${API_URL}auth/activation/confirm/`, {
    code,
    first_name: firstName.trim(),
    last_name: lastName.trim(),
    password,
  });
  applySession(data);
  return data;
};
