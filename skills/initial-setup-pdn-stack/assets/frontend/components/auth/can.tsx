"use client";

import type { ReactNode } from "react";

import { usePermissions } from "@/h/use-permissions";

interface CanProps {
  children: ReactNode;
  /** One codename. */
  permission?: string;
  /** Every codename listed (AND). */
  all?: readonly string[];
  /** At least one codename listed (OR). */
  any?: readonly string[];
  /** Rendered instead when the check fails. Defaults to nothing: hide, don't disable. */
  fallback?: ReactNode;
}

/**
 * Declarative permission gate for JSX:
 *
 *   <Can permission={PERMISSIONS.access.users.create}>…</Can>
 *   <Can all={[A, B]}>…</Can>
 *   <Can any={[A, B]}>…</Can>
 *
 * UI honesty, not authorization: the backend re-checks every request.
 */
const Can = ({ children, permission, all, any, fallback = null }: CanProps) => {
  const { can, canAll, canAny } = usePermissions();

  const allowed = permission ? can(permission) : all ? canAll(all) : any ? canAny(any) : true;

  return <>{allowed ? children : fallback}</>;
};

export default Can;
