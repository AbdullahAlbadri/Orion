"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";
import { useLang } from "@/lib/i18n";

export default function Header() {
  const { lang, setLang, t } = useLang();
  const { user, signOut } = useAuth();
  const router = useRouter();

  return (
    <header className="topbar">
      <Link href="/" className="wordmark" aria-label="Orion">
        {/* TODO: replace with the logo mark SVG once provided (public/brand/mark.svg) */}
        <span className="wordmark-ar">أوريون</span>
        <span className="wordmark-en">Orion</span>
      </Link>
      <nav className="topnav">
        {user && <Link href="/orders">{t("myOrders")}</Link>}
        <button className="link" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
          {t("switchLang")}
        </button>
        {user && (
          <button
            className="link"
            onClick={async () => {
              await signOut();
              router.replace("/login");
            }}
          >
            {t("logout")}
          </button>
        )}
      </nav>
    </header>
  );
}
