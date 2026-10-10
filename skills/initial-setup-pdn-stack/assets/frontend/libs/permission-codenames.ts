/**
 * Every permission the backend can grant, in one place.
 *
 * Mirrors `users/fixtures/permissions_catalog.json` in the backend. Use these
 * constants instead of typing strings: a typo becomes a compile error, and a
 * codename that silently matches nothing reads exactly like a user who lacks
 * the permission — the worst kind of bug to chase.
 *
 * Shape `module.resource.action`, written out per resource on purpose: a
 * generated `${resource}.create` would keep looking right the day one resource
 * stops following the pattern.
 *
 * This decides what the UI *offers*. The backend's `@required_perms` is what
 * actually authorizes.
 */
export const PERMISSIONS = {
  access: {
    users: {
      view: "access.users.view",
      create: "access.users.create",
      /** Also gates resending the invitation and sending a password reset. */
      edit: "access.users.edit",
      deactivate: "access.users.deactivate",
    },
    roles: {
      view: "access.roles.view",
      create: "access.roles.create",
      edit: "access.roles.edit",
      deactivate: "access.roles.deactivate",
    },
    permissions: {
      view: "access.permissions.view",
    },
  },
  organization: {
    settings: {
      view: "organization.settings.view",
      edit: "organization.settings.edit",
    },
  },
} as const;
