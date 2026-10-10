/** Pragmatic email check: one `@`, a dot in the domain, no whitespace. */
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/** Emails are logins: compared trimmed and lowercased, like the backend does. */
export const normalizeEmail = (value: string) => value.trim().toLowerCase();

export const isValidEmail = (value: string) => EMAIL_PATTERN.test(value.trim());

export interface PasswordRequirement {
  /** Mirrors the rule keys of `password_policy_failures` in the backend. */
  key: "min_length" | "uppercase" | "lowercase" | "digit" | "special" | "match";
  label: string;
  met: boolean;
}

const SPECIAL_CHARACTERS = /[!@#$%^&*(),.?":{}|<>_\-+=;'/\\[\]~`]/;

/**
 * The password policy, used wherever a password is *set* (activation, reset,
 * change). It mirrors `accounts.services.PASSWORD_RULES` in the backend, which
 * enforces it; keep both in sync. Signing in only checks that something was
 * typed — deciding whether it is right is the backend's job.
 */
export const getPasswordRequirements = (password: string, confirmation: string): PasswordRequirement[] => [
  { key: "min_length", label: "Al menos 8 caracteres", met: password.length >= 8 },
  { key: "uppercase", label: "Una letra mayúscula", met: /[A-Z]/.test(password) },
  { key: "lowercase", label: "Una letra minúscula", met: /[a-z]/.test(password) },
  { key: "digit", label: "Un número", met: /\d/.test(password) },
  { key: "special", label: "Un carácter especial (!@#$…)", met: SPECIAL_CHARACTERS.test(password) },
  { key: "match", label: "Las contraseñas coinciden", met: confirmation !== "" && password === confirmation },
];

export const meetsPasswordPolicy = (password: string, confirmation: string) =>
  getPasswordRequirements(password, confirmation).every((requirement) => requirement.met);
