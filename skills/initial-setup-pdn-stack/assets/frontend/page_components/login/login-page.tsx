"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { AxiosError } from "axios";

import { login } from "@/a/auth/login";
import { getApiCode, translateApiError } from "@/l/api-messages";
import { HOME_PATH, resetPasswordPath } from "@/l/routes";
import { isValidEmail } from "@/l/validators";

import ForgotPasswordForm from "./forgot-password-form";
import type { LoginStep } from "./types";

/**
 * Login at `/`. Structure and behaviour only — the visual design is decided
 * per project.
 *
 * The email typed here is kept when switching to "forgot password", so the
 * person never types it twice.
 */
const LoginPage = () => {
  const router = useRouter();
  const [step, setStep] = useState<LoginStep>("PASSWORD");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!isValidEmail(email) || !password) {
      setError("Escribe tu correo y tu contraseña.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      router.replace(HOME_PATH);
    } catch (failure) {
      // Right temporary password, but a new one is pending: the backend
      // withheld the session and handed a single-use code for the same page
      // the forgot-password email links to.
      if (getApiCode(failure) === "PASSWORD_CHANGE_REQUIRED") {
        const resetCode = (failure as AxiosError<{ reset_code?: string }>).response?.data?.reset_code;
        if (resetCode) {
          router.replace(resetPasswordPath(resetCode));
          return;
        }
      }
      setError(translateApiError(failure, "No pudimos iniciar sesión. Intenta de nuevo."));
      setLoading(false);
    }
  };

  if (step === "FORGOT_PASSWORD") {
    return <ForgotPasswordForm initialEmail={email} onBack={() => setStep("PASSWORD")} />;
  }

  return (
    <main>
      <h1>Iniciar sesión</h1>

      <form onSubmit={submit} noValidate>
        <label htmlFor="email">Correo electrónico</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          autoFocus
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {error && <p role="alert">{error}</p>}

        <button type="submit" disabled={loading}>
          {loading ? "Ingresando…" : "Iniciar sesión"}
        </button>
      </form>

      <button type="button" onClick={() => setStep("FORGOT_PASSWORD")} disabled={loading}>
        ¿Olvidaste tu contraseña?
      </button>
    </main>
  );
};

export default LoginPage;
