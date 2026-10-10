"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { confirmActivation, verifyActivationCode } from "@/a/auth/activation";
import { PasswordRequirements } from "@/c/auth";
import { getApiCode, translateApiError } from "@/l/api-messages";
import { HOME_PATH, LOGIN_PATH } from "@/l/routes";
import { getPasswordRequirements } from "@/l/validators";

type Step = "LOADING" | "VALID" | "INVALID" | "RETRY";

/** Answers that mean the invitation itself is dead. Anything else (rate
 * limit, network, server error) can be retried. */
const DEAD_LINK_CODES = new Set(["INVALID_CODE", "EXPIRED_CODE", "MISSING_CODE", "ALREADY_ACTIVATED"]);

/**
 * `/activate-account/[code]` — behind the invitation an administrator sends.
 *
 * Same three steps as the password reset: verify the code once, let the
 * person confirm their name and set a password, then land on /home with the
 * session the backend returns.
 */
const ActivateAccountPage = () => {
  const router = useRouter();
  const { code } = useParams<{ code: string }>();

  const [step, setStep] = useState<Step>("LOADING");
  const [attempt, setAttempt] = useState(0);
  const [reason, setReason] = useState("");
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Development mounts effects twice; verify each attempt once.
  const verifiedAttempt = useRef<number | null>(null);

  useEffect(() => {
    if (verifiedAttempt.current === attempt) return;
    verifiedAttempt.current = attempt;
    verifyActivationCode(code)
      .then((owner) => {
        setEmail(owner.email);
        setFirstName(owner.first_name);
        setLastName(owner.last_name);
        setStep("VALID");
      })
      .catch((failure) => {
        const dead = DEAD_LINK_CODES.has(getApiCode(failure) ?? "");
        setReason(translateApiError(failure, "No pudimos validar la invitación. Intenta de nuevo."));
        setStep(dead ? "INVALID" : "RETRY");
      });
  }, [code, attempt]);

  const retry = () => {
    setStep("LOADING");
    setAttempt((current) => current + 1);
  };

  const requirements = getPasswordRequirements(password, confirmation);
  const canSubmit =
    requirements.every((requirement) => requirement.met) && firstName.trim() !== "" && lastName.trim() !== "";

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) {
      setError("Completa tu nombre y una contraseña que cumpla todos los requisitos.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await confirmActivation({ code, firstName, lastName, password });
      router.replace(HOME_PATH);
    } catch (failure) {
      if (DEAD_LINK_CODES.has(getApiCode(failure) ?? "")) {
        setReason(translateApiError(failure, "La invitación ya no es válida."));
        setStep("INVALID");
        return;
      }
      setError(translateApiError(failure, "No pudimos activar tu cuenta. Intenta de nuevo."));
      setSaving(false);
    }
  };

  if (step === "LOADING") {
    return (
      <main aria-busy="true">
        <p>Verificando la invitación…</p>
      </main>
    );
  }

  if (step === "INVALID") {
    return (
      <main>
        <h1>Invitación no disponible</h1>
        <p>{reason}</p>
        <Link href={LOGIN_PATH}>Ir a iniciar sesión</Link>
      </main>
    );
  }

  if (step === "RETRY") {
    return (
      <main>
        <h1>No pudimos verificar la invitación</h1>
        <p>{reason}</p>
        <button type="button" onClick={retry}>
          Reintentar
        </button>
      </main>
    );
  }

  return (
    <main>
      <h1>Activa tu cuenta</h1>
      <p>
        Vas a activar <strong>{email}</strong>.
      </p>

      <form onSubmit={submit} noValidate>
        <label htmlFor="first-name">Nombres</label>
        <input
          id="first-name"
          autoComplete="given-name"
          value={firstName}
          onChange={(event) => setFirstName(event.target.value)}
        />

        <label htmlFor="last-name">Apellidos</label>
        <input
          id="last-name"
          autoComplete="family-name"
          value={lastName}
          onChange={(event) => setLastName(event.target.value)}
        />

        <label htmlFor="password">Contraseña</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
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

        <button type="submit" disabled={saving || !canSubmit}>
          {saving ? "Activando…" : "Activar cuenta"}
        </button>
      </form>
    </main>
  );
};

export default ActivateAccountPage;
