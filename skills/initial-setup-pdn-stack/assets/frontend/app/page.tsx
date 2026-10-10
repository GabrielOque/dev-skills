import type { Metadata } from "next";

import { LoginPage } from "@/pc/login";

export const metadata: Metadata = {
  title: "Iniciar sesión",
};

/** `/` — the login screen. Signed-in visitors are sent to /home by `proxy.ts`. */
export default function Page() {
  return <LoginPage />;
}
