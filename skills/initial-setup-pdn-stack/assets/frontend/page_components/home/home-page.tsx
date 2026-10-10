"use client";

import { logout } from "@/a/auth/logout";
import { Can } from "@/c/auth";
import { PERMISSIONS } from "@/l/permission-codenames";
import { useAppSelector } from "@/r/hooks";

/**
 * `/home` placeholder: proves the session end to end (profile from the store,
 * permission gating, logout). Replace it with the project's real landing
 * screen.
 */
const HomePage = () => {
  const user = useAppSelector((state) => state.auth.user);
  const organization = useAppSelector((state) => state.auth.organization);

  return (
    <main>
      <h1>Hola, {user?.full_name}</h1>
      <p>{organization?.name}</p>

      <Can permission={PERMISSIONS.access.users.view}>
        <p>Tienes acceso a la administración de usuarios.</p>
      </Can>

      <button type="button" onClick={() => void logout()}>
        Cerrar sesión
      </button>
    </main>
  );
};

export default HomePage;
