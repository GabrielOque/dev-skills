"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { logout } from "@/a/auth/logout";
import { ensureFreshSession } from "@/a/auth/refresh-token";

/**
 * Restores and refreshes the session on the client before the authenticated
 * UI renders.
 *
 * `proxy.ts` already checked the refresh token on the server, but it cannot
 * mint an access token nor refresh the persisted profile. This does both, and
 * signs the person out when the session turns out to be dead. Mounted once,
 * in `app/(app)/layout.tsx`.
 */
const SessionSync = ({ children, fallback = null }: { children: ReactNode; fallback?: ReactNode }) => {
  const [ready, setReady] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    // Development mounts effects twice; check the session once.
    if (started.current) return;
    started.current = true;

    void ensureFreshSession().then((alive) => {
      if (alive) setReady(true);
      else void logout();
    });
  }, []);

  return <>{ready ? children : fallback}</>;
};

export default SessionSync;
