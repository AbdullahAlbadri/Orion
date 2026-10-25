"use client";

import type { ReactNode } from "react";

import { AuthProvider } from "@/lib/auth";
import { LangProvider } from "@/lib/i18n";
import { MeProvider } from "@/lib/me";

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <LangProvider>
      <AuthProvider>
        <MeProvider>{children}</MeProvider>
      </AuthProvider>
    </LangProvider>
  );
}
