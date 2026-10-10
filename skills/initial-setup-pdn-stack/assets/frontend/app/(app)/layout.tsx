import { SessionSync } from "@/c/auth";

/**
 * Shell of every authenticated screen.
 *
 * `(app)` is a route group: it adds nothing to the URL (`/home`, and every
 * module the project adds next to it, share this layout). Next.js keeps it
 * mounted across navigations, so whatever shell the project builds here —
 * sidebar, header — never remounts.
 *
 * `SessionSync` refreshes the session first: the shell needs the current
 * permissions to decide what it may show.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionSync fallback={<p aria-busy="true">Cargando…</p>}>
      {/* The application shell (navigation, header) goes here. */}
      {children}
    </SessionSync>
  );
}
