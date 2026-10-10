/**
 * `user` as returned by login, refresh, activation, password reset and
 * `GET me/`. Field names are the backend's — ids are opaque UUID strings.
 */
export interface UserInfo {
  /** The business profile (`users.User`). */
  id: string;
  /** The login identity (`accounts.DjangoUser`). */
  django_user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  /**
   * Active role names. Display labels only — never authorize on a role name;
   * ask for a permission instead.
   */
  roles: string[];
  /**
   * Effective permission codenames: the union of every active role plus the
   * ones granted directly. Drives what the UI *offers*; the backend re-checks
   * every request with `@required_perms`.
   */
  permissions: string[];
  /** Django's full-access account. Detect it with this flag, never a role. */
  is_superuser: boolean;
  must_change_password: boolean;
}

export interface OrganizationInfo {
  id: string;
  name: string;
  slug: string;
}

/** `{access, refresh, user, organization}` — every way in ends with this. */
export interface AuthResponse {
  access: string;
  /** Present whenever the backend issues or rotates a refresh token. */
  refresh?: string;
  user: UserInfo;
  organization: OrganizationInfo;
}

/** The persisted part of the session (tokens live in cookies, not here). */
export interface SessionState {
  user: UserInfo | null;
  organization: OrganizationInfo | null;
}

/** Who an activation or reset link belongs to, once the code checks out. */
export interface CodeOwner {
  email: string;
  first_name: string;
  last_name: string;
}
