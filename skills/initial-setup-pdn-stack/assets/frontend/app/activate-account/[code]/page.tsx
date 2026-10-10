import type { Metadata } from "next";

import { ActivateAccountPage } from "@/pc/activate-account";

export const metadata: Metadata = {
  title: "Activa tu cuenta",
};

/** Public page behind the invitation link. */
export default function Page() {
  return <ActivateAccountPage />;
}
