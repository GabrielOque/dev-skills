import type { AxiosError } from "axios";

import type { ApiErrorBody } from "@/t/api";

/**
 * The copy a person reads for every `code` the backend returns.
 *
 * The API answers in English with a stable, machine-readable `code`; the words
 * shown in the UI are chosen here. That keeps display copy out of the backend
 * and lets wording change without touching an endpoint. The backend's own
 * `message` is for logs and developers — never render it.
 *
 * Adding an endpoint? Add its codes here in the same change: an unmapped code
 * falls back to the caller's generic sentence, which is safe but unhelpful.
 */
const API_MESSAGES: Record<string, string> = {
  // --- Session and access ---
  AUTHENTICATION_REQUIRED: "Tu sesión expiró. Vuelve a iniciar sesión.",
  TOKEN_INVALID: "Tu sesión expiró. Vuelve a iniciar sesión.",
  PERMISSION_DENIED: "No tienes permiso para realizar esta acción.",
  NO_PROFILE: "Tu cuenta no tiene acceso a la aplicación. Contacta al administrador.",
  INVALID_CREDENTIALS: "Correo o contraseña incorrectos.",
  INACTIVE_USER: "Tu cuenta no está activa. Contacta al administrador.",
  USER_OR_ORGANIZATION_ARCHIVED: "Tu cuenta está desactivada. Contacta al administrador.",
  USER_NOT_FOUND: "No encontramos tu cuenta.",
  PASSWORD_CHANGE_REQUIRED: "Debes definir una contraseña nueva para continuar.",
  TOO_MANY_REQUESTS: "Demasiados intentos. Espera un momento y vuelve a intentarlo.",

  // --- Activation and password-reset links ---
  MISSING_CODE: "El enlace está incompleto.",
  INVALID_CODE: "El enlace no es válido o ya fue usado.",
  EXPIRED_CODE: "El enlace venció. Solicita uno nuevo.",
  ALREADY_ACTIVATED: "Esta cuenta ya fue activada. Inicia sesión.",
  PASSWORD_RESET_REQUESTED: "Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña.",

  // --- Passwords ---
  WEAK_PASSWORD: "La contraseña no cumple los requisitos de seguridad.",
  INVALID_PASSWORD: "La contraseña actual no es correcta.",
  SAME_PASSWORD: "La contraseña nueva debe ser distinta de la actual.",
  PASSWORD_CHANGED: "Tu contraseña fue actualizada.",

  // --- Validation and generic ---
  VALIDATION_ERROR: "Revisa los datos: hay campos inválidos.",
  MISSING_FIELDS: "Faltan campos obligatorios.",
  MALFORMED_REQUEST: "No pudimos procesar la solicitud.",
  NOT_FOUND: "No encontramos lo que buscas.",
  METHOD_NOT_ALLOWED: "Esta acción no está disponible.",
  ALREADY_ARCHIVED: "El registro ya estaba desactivado.",
  NOT_ARCHIVED: "El registro ya estaba activo.",

  // --- Users ---
  EMAIL_TAKEN: "Ya existe un usuario con ese correo.",
  INVALID_ROLE: "Uno de los roles no existe.",
  INVALID_PERMISSION: "Uno de los permisos no existe.",
  CANNOT_DEACTIVATE_SELF: "No puedes desactivar tu propio usuario.",
  USER_ARCHIVED: "El usuario está desactivado.",
  EMAIL_NOT_SENT: "No pudimos enviar el correo. Intenta de nuevo más tarde.",
  INVITATION_SENT: "Enviamos una nueva invitación.",
  PASSWORD_RESET_SENT: "Enviamos el enlace para restablecer la contraseña.",

  // --- Roles ---
  ROLE_NAME_TAKEN: "Ya existe un rol con ese nombre.",
};

const NETWORK_ERROR_MESSAGE = "No pudimos conectar con el servidor. Revisa tu conexión.";

/** The backend's `code` for this error, when there is one. Use it for control flow. */
export const getApiCode = (error: unknown): string | undefined =>
  (error as AxiosError<ApiErrorBody>)?.response?.data?.code;

/** The copy for a code, or undefined when it is not mapped. */
export const apiMessage = (code: string | undefined): string | undefined =>
  code ? API_MESSAGES[code] : undefined;

/**
 * What to tell the person: the mapped `code`, then a network failure, then
 * `fallback`. Never the backend's `message`.
 */
export const translateApiError = (error: unknown, fallback: string): string => {
  const mapped = apiMessage(getApiCode(error));
  if (mapped) return mapped;
  if (!(error as AxiosError)?.response) return NETWORK_ERROR_MESSAGE;
  return fallback;
};
