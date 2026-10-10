"use client";

import type { ReactNode } from "react";

import ReduxProvider from "@/r/provider";

/**
 * Every client-side provider the app needs, composed in one place. Add new
 * ones here (theme, notifications, query cache…) rather than in layouts.
 */
export default function Providers({ children }: { children: ReactNode }) {
  return <ReduxProvider>{children}</ReduxProvider>;
}
