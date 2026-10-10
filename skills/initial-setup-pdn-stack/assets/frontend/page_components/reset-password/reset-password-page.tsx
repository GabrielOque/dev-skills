"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { confirmPasswordReset, verifyPasswordResetCode } from "@/a/auth/password-reset";
import { PasswordRequirements } from "@/c/auth";
import { getApiCode, translateApiError } from "@/l/api-messages";
import { HOME_PATH, LOGIN_PATH } from "@/l/routes";
import { getPasswordRequirements } from "@/l/validators";
import type { CodeOwner } from "@/t/auth";

type Step = "LOADING" | "VALID" | "INVALID" | "RETRY";

/** Answers that mean the link itself is dead. Anything else (rate limit,
 * network, server error) says nothing about the link and can be retried. */
const DEAD_LINK_CODES = new Set(["INVALID_CODE", "EXPIRED_CODE", "MISSING_CODE", "INACTIVE_USER"]);

/**
 * `/reset-password/[code]` — behind the emailed link, and where a forced
 * password change (`PASSWORD_CHANGE_REQUIRED` at login) lands.
 *
 * 1. LOADING: the code is checked once against the backend.
 * 2. VALID: the person sets a password that meets the live checklist.
 * 3. The backend answers with a full session, so they land on /home signed in.
 * INVALID is terminal (the only way forward is a new link); RETRY is not.
 */
const ResetPasswordPage = () => {
  const router = useRouter();
  const { code } = useParams<{ code: string }>();

  const [step, setStep] = useState<Step>("LOADING");
  const [attempt, setAttempt] = useState(0);
  const [owner, setOwner] = useState<CodeOwner | null>(null);
  const [reason, setReason] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Development mounts effects twice; verify each attempt once.
  const verifiedAttempt = useRef<number | null>(null);

  useEffect(() => {
    if (verifiedAttempt.current === attempt) return;
    verifiedAttempt.current = attempt;
    verifyPasswordResetCode(code)
      .then((found) => {
        setOwner(found);
        setStep("VALID");
      })
      .catch((failure) => {
        const dead = DEAD_LINK_CODES.has(getApiCode(failure) ?? "");
        setReason(translateApiError(failure, "No pudimos validar el enlace. Intenta de nuevo."));
        setStep(dead ? "INVALID" : "RETRY");
      });
  }, [code, attempt]);

  const retry = () => {
    setStep("LOADING");
    setAttempt((current) => current + 1);
  };

  const requirements = getPasswordRequirements(password, confirmation);
  const meetsPolicy = requirements.every((requirement) => requirement.met);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!meetsPolicy) {
      setError("La contraseña aún no cumple todos los requisitos.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await confirmPasswordReset(code, password);
      router.replace(HOME_PATH);
    } catch (failure) {
      // The link died between opening the page and submitting it.
      if (DEAD_LINK_CODES.has(getApiCode(failure) ?? "")) {
        setReason(translateApiError(failure, "El enlace ya no es válido."));
        setStep("INVALID");
        return;
      }
      setError(translateApiError(failure, "No pudimos cambiar la contraseña. Intenta de nuevo."));
      setSaving(false);
    }
  };

  if (step === "LOADING") {
    return (
      <main aria-busy="true">
        <p>Verificando el enlace…</p>
      </main>
    );
  }

  if (step === "INVALID") {
    return (
      <main>
        <h1>Enlace inválido o vencido</h1>
        <p>{reason}</p>
        <Link href={LOGIN_PATH}>Ir a iniciar sesión</Link>
      </main>
    );
  }

  if (step === "RETRY") {
    return (
      <main>
        <h1>No pudimos verificar el enlace</h1>
        <p>{reason}</p>
        <button type="button" onClick={retry}>
          Reintentar
        </button>
      </main>
    );
  }

  return (
    <main>
      <h1>Crea una contraseña nueva</h1>
      <p>
        Para <strong>{owner?.email}</strong>.
      </p>

      <form onSubmit={submit} noValidate>
        <label htmlFor="password">Contraseña nueva</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          autoFocus
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        <label htmlFor="confirmation">Confirma la contraseña</label>
        <input
          id="confirmation"
          type="password"
          autoComplete="new-password"
          value={confirmation}
          onChange={(event) => setConfirmation(event.target.value)}
        />

        <PasswordRequirements requirements={requirements} />

        {error && <p role="alert">{error}</p>}

        <button type="submit" disabled={saving || !meetsPolicy}>
          {saving ? "Guardando…" : "Cambiar contraseña"}
        </button>
      </form>
    </main>
  );
};

export default ResetPasswordPage;
