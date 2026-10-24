import type { Metadata } from "next";
import { IBM_Plex_Sans_Arabic, Work_Sans } from "next/font/google";
import type { ReactNode } from "react";

import Header from "@/components/Header";
import Providers from "./providers";
import "./globals.css";

// Brand: Work Sans SemiBold (Latin). Arabic brand font is Swissra Bold (licensed, not bundled yet);
// IBM Plex Sans Arabic stands in until the licence files are added.
const workSans = Work_Sans({ subsets: ["latin"], weight: ["400", "600"], variable: "--font-latin", display: "swap" });
const plexArabic = IBM_Plex_Sans_Arabic({
  subsets: ["arabic"], weight: ["400", "600", "700"], variable: "--font-arabic", display: "swap",
});

export const metadata: Metadata = {
  title: "أوريون | Orion",
  description: "Custom products from the right manufacturer, handled end to end.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ar" dir="rtl" className={`${workSans.variable} ${plexArabic.variable}`} suppressHydrationWarning>
      <body>
        <Providers>
          <Header />
          <main className="container">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
