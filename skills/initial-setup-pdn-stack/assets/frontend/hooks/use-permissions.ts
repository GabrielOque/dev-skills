"use client";

import { useMemo } from "react";

import { buildPermissionContext, hasAllPermissions, hasAnyPermission } from "@/l/permissions";
import { useAppSelector } from "@/r/hooks";

export interface UsePermissionsResult {
  /** True when the user holds this codename. Superusers hold everything. */
  can: (codename: string) => boolean;
  /** True only when the user holds **every** codename listed. */
  canAll: (codenames: readonly string[]) => boolean;
  /** True when the user holds at least one — e.g. whether a menu is worth showing. */
  canAny: (codenames: readonly string[]) => boolean;
  isSuperuser: boolean;
}

/**
 * What the signed-in user may do, anywhere in the app.
 *
 * **Not authorization**: the backend re-checks every call. Hiding an action
 * the API would refuse only stops the UI from promising what it cannot do.
 * Hide denied controls — don't disable them. Use the constants in
 * `@/l/permission-codenames`, never typed strings.
 *
 * @example
 * const { can } = usePermissions();
 * {can(PERMISSIONS.access.users.create) && <button>…</button>}
 */
export const usePermissions = (): UsePermissionsResult => {
  const user = useAppSelector((state) => state.auth.user);

  return useMemo(() => {
    const context = buildPermissionContext(user);
    return {
      can: (codename) => hasAllPermissions([codename], context),
      canAll: (codenames) => hasAllPermissions(codenames, context),
      canAny: (codenames) => hasAnyPermission(codenames, context),
      isSuperuser: context.isSuperuser,
    };
  }, [user]);
};

export default usePermissions;
