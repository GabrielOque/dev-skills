import type { Metadata } from "next";

import { HomePage } from "@/pc/home";

export const metadata: Metadata = {
  title: "Inicio",
};

/** `/home` — where every signed-in user lands. */
export default function Page() {
  return <HomePage />;
}
