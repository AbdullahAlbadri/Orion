import type { Metadata } from "next";
import { Cairo, Work_Sans } from "next/font/google";
import type { ReactNode } from "react";

import AppShell from "@/components/AppShell";
import { thDisplay, thSans } from "./fonts";
import Providers from "./providers";
import "./globals.css";

// Thmanyah (fonts.ts) is the site font in both languages; Work Sans and Cairo are fallbacks when it is missing.
const workSans = Work_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-latin", display: "swap" });
const arabic = Cairo({
  subsets: ["arabic"], weight: ["400", "500", "600", "700"], variable: "--font-arabic", display: "swap",
});

export const metadata: Metadata = {
  title: "أوريون | Orion",
  description: "Custom products from the right manufacturer, handled end to end.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ar" dir="rtl" className={`${workSans.variable} ${arabic.variable} ${thSans.variable} ${thDisplay.variable}`} suppressHydrationWarning>
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
