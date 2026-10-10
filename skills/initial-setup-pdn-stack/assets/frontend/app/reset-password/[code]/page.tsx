import type { Metadata } from "next";

import { ResetPasswordPage } from "@/pc/reset-password";

export const metadata: Metadata = {
  title: "Restablecer contraseña",
};

/** Public page behind the emailed reset link (and the forced password change). */
export default function Page() {
  return <ResetPasswordPage />;
}
