import type { Metadata } from "next";

import "./globals.css";
import Providers from "@/c/providers";

export const metadata: Metadata = {
  title: {
    template: "%s · {{PROJECT_NAME}}",
    default: "{{PROJECT_NAME}}",
  },
};

/**
 * Root layout: document shell and client providers only. Fonts, theme and
 * any visual chrome are design decisions made per project.
 */
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="{{HTML_LANG}}">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
