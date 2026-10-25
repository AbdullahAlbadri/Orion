import type { Metadata } from "next";
import { Cairo, Work_Sans } from "next/font/google";
import type { ReactNode } from "react";

import AppShell from "@/components/AppShell";
import TopoBackground from "@/components/TopoBackground";
import Providers from "./providers";
import "./globals.css";

// Brand: Work Sans SemiBold (Latin). Arabic brand font is Swissra Bold (paid licence, not bundled);
// Cairo stands in until licensed web font files are added (docs/website/landing-redesign.md).
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
    <html lang="ar" dir="rtl" className={`${workSans.variable} ${arabic.variable}`} suppressHydrationWarning>
      <body>
        <TopoBackground />
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
