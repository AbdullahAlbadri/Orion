"use client";

// Sidebar layout. The sidebar sits on the start side, so it moves to the right automatically in Arabic.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "@/lib/auth";
import { useLang } from "@/lib/i18n";
import { BoxIcon, GlobeIcon, HomeIcon, LogoutIcon, PlusIcon } from "./Icons";

export function Logo() {
  return (
    <Link href="/" className="logo" aria-label="Orion">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/brand/mark-gold.png" alt="" width={38} height={36} />
      <span className="logo-text">
        <span className="logo-ar">أوريون</span>
        <span className="logo-en">Orion</span>
      </span>
    </Link>
  );
}

export default function AppShell({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth();
  const { lang, setLang, t } = useLang();
  const pathname = usePathname();
  const router = useRouter();

  if (!user) return <div className="public">{children}</div>;

  const nav = [
    { href: "/orders", label: t("overview"), icon: <HomeIcon /> },
    { href: "/orders#list", label: t("myOrders"), icon: <BoxIcon /> },
    { href: "/orders/new", label: t("newOrder"), icon: <PlusIcon /> },
  ];

  return (
    <div className="shell">
      <aside className="sidebar">
        <Logo />
        <nav className="side-nav" aria-label={t("menu")}>
          {nav.map((item) => (
            <Link key={item.href} href={item.href}
              className={`side-link${pathname === item.href.split("#")[0] && !item.href.includes("#") ? " active" : ""}`}>
              {item.icon}
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
        <div className="side-bottom">
          <button className="side-link" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
            <GlobeIcon /><span>{t("switchLang")}</span>
          </button>
          <button className="side-link" onClick={async () => { await signOut(); router.replace("/login"); }}>
            <LogoutIcon /><span>{t("logout")}</span>
          </button>
        </div>
        <div className="blob blob-a" aria-hidden />
        <div className="blob blob-b" aria-hidden />
        <div className="blob blob-c" aria-hidden />
      </aside>
      <div className="content">
        <header className="topbar">
          <div>
            <div className="muted small">{t("welcome")}</div>
            <div className="who" dir="ltr">{user.email}</div>
          </div>
          <Link href="/orders/new" className="btn btn-sm"><PlusIcon width={18} height={18} /> {t("newOrder")}</Link>
        </header>
        <main className="page">{children}</main>
      </div>
    </div>
  );
}
