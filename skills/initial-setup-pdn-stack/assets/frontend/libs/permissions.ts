import type { UserInfo } from "@/t/auth";

/**
 * Permission evaluation, free of React, so every surface (navigation, route
 * guards, buttons, row actions) reaches the same verdict from the same code.
 * Components never write `permissions.includes(...)` themselves — they use
 * `usePermissions()` or `<Can>`.
 */
export interface PermissionContext {
  granted: Set<string>;
  /** Django's full-access account short-circuits every check. */
  isSuperuser: boolean;
}

export const buildPermissionContext = (user: Partial<UserInfo> | null | undefined): PermissionContext => ({
  granted: new Set(user?.permissions ?? []),
  isSuperuser: user?.is_superuser === true,
});

/**
 * True when the user holds **every** listed codename (AND). An empty list is
 * ungated on purpose: a new screen stays visible until someone decides which
 * codename guards it.
 */
export const hasAllPermissions = (required: readonly string[] | undefined, context: PermissionContext) =>
  context.isSuperuser || !required?.length || required.every((codename) => context.granted.has(codename));

/** True when the user holds at least one listed codename (OR). */
export const hasAnyPermission = (required: readonly string[] | undefined, context: PermissionContext) =>
  context.isSuperuser || !required?.length || required.some((codename) => context.granted.has(codename));
