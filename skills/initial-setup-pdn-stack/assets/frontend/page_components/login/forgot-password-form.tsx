"use client";

import { useState, type FormEvent } from "react";

import { requestPasswordReset } from "@/a/auth/password-reset";
import { apiMessage, translateApiError } from "@/l/api-messages";
import { isValidEmail } from "@/l/validators";

interface ForgotPasswordFormProps {
  initialEmail?: string;
  onBack: () => void;
}

/**
 * Asks for a reset link. The confirmation reads the same whether or not the
 * email is registered — the backend never says which accounts exist, and
 * neither does the UI.
 */
const ForgotPasswordForm = ({ initialEmail = "", onBack }: ForgotPasswordFormProps) => {
  const [email, setEmail] = useState(initialEmail);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!isValidEmail(email)) {
      setError("Escribe un correo electrónico válido.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (failure) {
      setError(translateApiError(failure, "No pudimos enviar el enlace. Intenta de nuevo."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <h1>¿Olvidaste tu contraseña?</h1>

      {sent ? (
        <p role="status">{apiMessage("PASSWORD_RESET_REQUESTED")}</p>
      ) : (
        <form onSubmit={submit} noValidate>
          <p>Escribe el correo de tu cuenta y te enviaremos un enlace para crear una contraseña nueva.</p>

          <label htmlFor="reset-email">Correo electrónico</label>
          <input
            id="reset-email"
            type="email"
            autoComplete="email"
            autoFocus
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />

          {error && <p role="alert">{error}</p>}

          <button type="submit" disabled={loading}>
            {loading ? "Enviando…" : "Enviar enlace"}
          </button>
        </form>
      )}

      <button type="button" onClick={onBack} disabled={loading}>
        Volver a iniciar sesión
      </button>
    </main>
  );
};

export default ForgotPasswordForm;
