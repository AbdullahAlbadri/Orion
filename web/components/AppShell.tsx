"use client";

// Signed-in layout (docs/website/00-sitemap.md "Navigation"): a 7-entry sidebar; a header with Messages
// (bell + unread count), Help, language and the account menu; on phones a bottom bar with a centre
// "new order" button and a "More" sheet. The sidebar sits on the start side, so it is on the right in Arabic.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { api, type Notification } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ago, NAV } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";
import {
  BellIcon, BoxIcon, BuildingIcon, CardIcon, ChartIcon, GearIcon, GlobeIcon, HelpIcon, HomeIcon, LogoutIcon,
  MenuIcon, PlusIcon, ShirtIcon, TruckIcon, UserIcon,
} from "./Icons";
import "../app/app.css";

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

const SIDEBAR = [
  { href: "/dashboard", label: NAV.overview, icon: <HomeIcon /> },
  { href: "/orders", label: NAV.orders, icon: <BoxIcon />, also: ["/orders/"] },
  { href: "/shipments", label: NAV.shipments, icon: <TruckIcon /> },
  { href: "/products", label: NAV.products, icon: <ShirtIcon />, also: ["/products/"] },
  { href: "/payments", label: NAV.payments, icon: <CardIcon />, also: ["/documents"] },
  { href: "/stats", label: NAV.stats, icon: <ChartIcon /> },
  { href: "/settings", label: NAV.settings, icon: <GearIcon /> },
];

function isActive(pathname: string, item: { href: string; also?: string[] }) {
  return pathname === item.href || (item.also ?? []).some((p) => pathname.startsWith(p));
}

export default function AppShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { lang } = useLang();
  const pathname = usePathname();
  const [more, setMore] = useState(false);

  useEffect(() => setMore(false), [pathname]);

  // The landing page is its own full-width page; sign-in and onboarding are centred; everything else is the app
  if (pathname === "/") return <>{children}</>;
  if (!user || pathname.startsWith("/start") || pathname.startsWith("/login")) return <div className="public">{children}</div>;

  const L = (x: Record<"ar" | "en", string>) => x[lang];
  return (
    <div className="shell">
      <aside className="sidebar">
        <Logo />
        <nav className="side-nav" aria-label={L(NAV.account)}>
          {SIDEBAR.map((item) => (
            <Link key={item.href} href={item.href} className={`side-link${isActive(pathname, item) ? " active" : ""}`}
              aria-current={isActive(pathname, item) ? "page" : undefined}>
              {item.icon}<span>{L(item.label)}</span>
            </Link>
          ))}
        </nav>
        <div className="side-bottom">
          <Link href="/help" className={`side-link${pathname === "/help" ? " active" : ""}`}><HelpIcon /><span>{L(NAV.help)}</span></Link>
        </div>
        <div className="blob blob-a" aria-hidden />
        <div className="blob blob-b" aria-hidden />
        <div className="blob blob-c" aria-hidden />
      </aside>

      <div className="content">
        <Header />
        <main className="page">{children}</main>
      </div>

      <nav className="bottom-bar" aria-label={L(NAV.account)}>
        <Link href="/dashboard" className={pathname === "/dashboard" ? "on" : ""}><HomeIcon /><span>{L(NAV.overview)}</span></Link>
        <Link href="/orders" className={pathname.startsWith("/orders") && pathname !== "/orders/new" ? "on" : ""}><BoxIcon /><span>{L(NAV.orders)}</span></Link>
        <Link href="/orders/new" className="bottom-new" aria-label={L(NAV.newOrder)}><PlusIcon /></Link>
        <Link href="/shipments" className={pathname === "/shipments" ? "on" : ""}><TruckIcon /><span>{L(NAV.shipments)}</span></Link>
        <button type="button" onClick={() => setMore(true)}><MenuIcon /><span>{L(NAV.more)}</span></button>
      </nav>
      {more && <MoreSheet onClose={() => setMore(false)} />}
    </div>
  );
}

function Header() {
  const { lang, setLang } = useLang();
  const { me, unread, refreshUnread } = useMe();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const [open, setOpen] = useState<"bell" | "account" | null>(null);
  const [latest, setLatest] = useState<Notification[] | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const pathname = usePathname();

  useEffect(() => setOpen(null), [pathname]);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(null); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(null); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const openBell = async () => {
    if (open === "bell") return setOpen(null);
    setOpen("bell");
    const r = await api<{ items: Notification[]; unread: number }>("/notifications").catch(() => null);
    setLatest(r ? r.items.slice(0, 4) : []);
    refreshUnread().catch(() => {});
  };

  return (
    <header className="topbar" ref={box}>
      <div className="topbar-hello">
        <Link href="/dashboard" className="topbar-logo" aria-label="Orion">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/mark-gold.png" alt="" width={30} height={28} />
        </Link>
        <div>
          <div className="muted small">{L(NAV.hello)}</div>
          <div className="who">{me?.name || me?.email || ""}</div>
        </div>
      </div>
      <div className="topbar-actions">
        <Link href="/orders/new" className="btn btn-sm hide-phone"><PlusIcon width={18} height={18} /> {L(NAV.newOrder)}</Link>
        <div className="pop-anchor">
          <button type="button" className="icon-btn" aria-label={`${L(NAV.messages)}${unread ? ` (${unread})` : ""}`}
            aria-expanded={open === "bell"} onClick={openBell}>
            <BellIcon width={20} height={20} />
            {unread > 0 && <span className="badge">{unread > 9 ? "9+" : unread}</span>}
          </button>
          {open === "bell" && (
            <div className="popover">
              <strong>{L(NAV.messages)}</strong>
              {latest === null ? <p className="muted small">…</p> : latest.length === 0 ? (
                <p className="muted small">{L(NAV.noUpdates)}</p>
              ) : latest.map((n) => (
                <Link key={n.id} href={n.href || "/messages"} className={`pop-item${n.read_at ? "" : " unread"}`}>
                  <span>{lang === "ar" ? n.title_ar : n.title_en}</span>
                  <span className="muted small">{ago(n.created_at, lang)}</span>
                </Link>
              ))}
              <Link href="/messages" className="pop-all">{L(NAV.seeAll)}</Link>
            </div>
          )}
        </div>
        <Link href="/help" className="icon-btn hide-phone" aria-label={L(NAV.help)}><HelpIcon width={20} height={20} /></Link>
        <button type="button" className="icon-btn" onClick={() => setLang(lang === "ar" ? "en" : "ar")}
          aria-label={lang === "ar" ? "English" : "العربية"} title={lang === "ar" ? "English" : "العربية"}>
          <GlobeIcon width={20} height={20} />
        </button>
        <div className="pop-anchor">
          <button type="button" className="icon-btn" aria-label={L(NAV.account)} aria-expanded={open === "account"}
            onClick={() => setOpen(open === "account" ? null : "account")}>
            <UserIcon width={20} height={20} />
          </button>
          {open === "account" && <AccountMenu />}
        </div>
      </div>
    </header>
  );
}

function AccountMenu() {
  const { lang } = useLang();
  const { signOut } = useAuth();
  const router = useRouter();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  return (
    <div className="popover menu">
      <Link href="/business"><BuildingIcon width={18} height={18} /> {L(NAV.business)}</Link>
      <Link href="/settings"><GearIcon width={18} height={18} /> {L(NAV.settings)}</Link>
      <button type="button" onClick={async () => { await signOut(); router.replace("/"); }}>
        <LogoutIcon width={18} height={18} /> {L(NAV.signOut)}
      </button>
    </div>
  );
}

function MoreSheet({ onClose }: { onClose: () => void }) {
  const { lang } = useLang();
  const { signOut } = useAuth();
  const router = useRouter();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  const items = [
    { href: "/products", label: NAV.products, icon: <ShirtIcon /> },
    { href: "/payments", label: NAV.payments, icon: <CardIcon /> },
    { href: "/stats", label: NAV.stats, icon: <ChartIcon /> },
    { href: "/messages", label: NAV.messages, icon: <BellIcon /> },
    { href: "/help", label: NAV.help, icon: <HelpIcon /> },
    { href: "/business", label: NAV.business, icon: <BuildingIcon /> },
    { href: "/settings", label: NAV.settings, icon: <GearIcon /> },
  ];
  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label={L(NAV.more)} onClick={(e) => e.stopPropagation()}>
        {items.map((i) => <Link key={i.href} href={i.href}>{i.icon}<span>{L(i.label)}</span></Link>)}
        <button type="button" onClick={async () => { await signOut(); router.replace("/"); }}><LogoutIcon /><span>{L(NAV.signOut)}</span></button>
      </div>
    </div>
  );
}
