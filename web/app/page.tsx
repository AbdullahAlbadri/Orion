"use client";

// Home (docs/website/01-home.md): one long page with anchored sections and a sticky header.
import Link from "next/link";
import { useState, type ReactNode } from "react";

import {
  ArrowIcon, BookIcon, BoxIcon, CheckIcon, GlobeIcon, HeartIcon, LayersIcon, ShieldIcon, ShirtIcon, SparkleIcon,
} from "@/components/Icons";
import LegalDrawer from "@/components/LegalDrawer";
import TopoTexture from "@/components/TopoTexture";
import { useAuth } from "@/lib/auth";
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";

const MARKET_ICONS: Record<string, ReactNode> = {
  shirt: <ShirtIcon />, book: <BookIcon />, layers: <LayersIcon />, sparkle: <SparkleIcon />, heart: <HeartIcon />, box: <BoxIcon />,
};

export default function Home() {
  const { lang, setLang } = useLang();
  const { user } = useAuth();
  const [market, setMarket] = useState<string | null>("apparel");
  const [legal, setLegal] = useState(false);
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const startHref = user ? "/orders/new" : "/start";
  const selected = HOME.markets.items.find((m) => m.id === market);

  return (
    <div className="home">
      <header className="home-header">
        <Link href="/" className="logo" aria-label="Orion">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/mark-gold.png" alt="" width={34} height={32} />
          <span className="logo-text"><span className="logo-ar">أوريون</span><span className="logo-en">Orion</span></span>
        </Link>
        <nav className="home-nav">
          <a href="#how">{L(HOME.nav.how)}</a>
          <a href="#markets">{L(HOME.nav.markets)}</a>
          <a href="#pricing">{L(HOME.nav.pricing)}</a>
          <a href="#faq">{L(HOME.nav.faq)}</a>
          <a href="#trust">{L(HOME.nav.trust)}</a>
        </nav>
        <div className="row">
          <button type="button" className="btn-ghost btn-sm" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
            <GlobeIcon width={16} height={16} /> {lang === "ar" ? "English" : "العربية"}
          </button>
          {user
            ? <Link href="/dashboard" className="btn-ghost btn-sm">{L(HOME.nav.dashboard)}</Link>
            : <Link href="/start" className="btn-ghost btn-sm hide-sm">{L(HOME.nav.signIn)}</Link>}
          <Link href={startHref} className="btn btn-sm">{L(HOME.nav.start)}</Link>
        </div>
      </header>

      <section className="hero-section">
        <div className="hero-copy">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="hero-mark" src="/brand/mark-gold.png" alt="" />
          <h1 className="hero-title">{L(HOME.hero.title)}</h1>
          <p className="hero-sub">{L(HOME.hero.sub)}</p>
          <div className="row">
            <Link href={startHref} className="btn">{L(HOME.nav.start)} <ArrowIcon className="flip-forward" width={18} height={18} /></Link>
            <a href="#how" className="btn-ghost">{L(HOME.hero.secondary)}</a>
          </div>
        </div>
      </section>

      <main className="home-main">
        <Section id="problem" title={L(HOME.problem.title)}>
          <div className="grid-3">
            {HOME.problem.items.map((p, i) => (
              <div key={i} className={`board cross ${["board-ink", "board-paper", "board-signal"][i]}`}>
                {i === 0 && <TopoTexture />}
                <h3>{L(p.title)}</h3>
                <p className={i === 0 ? "muted" : ""} style={{ margin: 0 }}>{L(p.text)}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section id="how" title={L(HOME.how.title)}>
          <ol className="steps-row">
            {HOME.how.steps.map((s, i) => (
              <li key={i} className="board board-glass cross">
                <span className="step-num">{i + 1}</span>
                <h3>{L(s.title)}</h3>
                <p className="muted" style={{ margin: 0 }}>{L(s.text)}</p>
              </li>
            ))}
          </ol>
        </Section>

        <Section id="markets" title={L(HOME.markets.title)} sub={L(HOME.markets.sub)}>
          <div className="market-grid">
            {HOME.markets.items.map((m) => (
              <button key={m.id} type="button" className={`market-card${market === m.id ? " active" : ""}`}
                aria-expanded={market === m.id} onClick={() => setMarket(market === m.id ? null : m.id)}>
                <span className="market-icon">{MARKET_ICONS[m.icon]}</span>
                <strong>{L(m.name)}</strong>
                <span className={`pill ${m.live ? "you" : "draft"}`}>{m.live ? L(HOME.markets.live) : L(HOME.markets.soon)}</span>
              </button>
            ))}
          </div>
          {selected && (
            <div className="board board-ink cross market-panel">
              <TopoTexture />
              <h3>{L(selected.name)}</h3>
              <div className="grid-2">
                <div><div className="muted small">{L(HOME.markets.options)}</div><p>{L(selected.options)}</p></div>
                <div><div className="muted small">{L(HOME.markets.asked)}</div><p>{L(selected.asked)}</p></div>
              </div>
              {selected.live
                ? <Link href={user ? `/orders/new?market=${selected.id}` : "/start"} className="btn" style={{ alignSelf: "flex-start" }}>
                    {L(HOME.markets.startHere)}</Link>
                : <span className="muted">{L(HOME.markets.soonNote)}</span>}
            </div>
          )}
        </Section>

        <Section id="pricing" title={L(HOME.pricing.title)}>
          <div className="grid-4">
            {HOME.pricing.parts.map((p, i) => (
              <div key={i} className="board board-glass cross">
                <span className="step-num">+</span>
                <h3>{L(p.title)}</h3>
                <p className="muted" style={{ margin: 0 }}>{L(p.text)}</p>
              </div>
            ))}
          </div>
          <ul className="promise-list">
            {HOME.pricing.promises.map((p, i) => <li key={i}><CheckIcon width={18} height={18} /> {L(p)}</li>)}
          </ul>
        </Section>

        <Section id="faq" title={L(HOME.faq.title)}>
          <div className="faq">
            {HOME.faq.items.map((f, i) => (
              <details key={i} className="board board-glass">
                <summary>{L(f.q)}</summary>
                <p className="muted" style={{ margin: "10px 0 0" }}>{L(f.a)}</p>
              </details>
            ))}
          </div>
        </Section>

        <Section id="trust" title={L(HOME.trust.title)}>
          <div className="grid-3">
            {HOME.trust.items.map((x, i) => (
              <div key={i} className="board board-ink cross">
                <TopoTexture />
                <span className="market-icon"><ShieldIcon /></span>
                <h3>{L(x.title)}</h3>
                <p className="muted" style={{ margin: 0 }}>{L(x.text)}</p>
              </div>
            ))}
          </div>
        </Section>

        <section className="cta-band board board-signal cross">
          <h2 style={{ margin: 0 }}>{L(HOME.hero.title)}</h2>
          <Link href={startHref} className="btn">{L(HOME.nav.start)}</Link>
        </section>
      </main>

      <footer className="home-footer">
        <span className="muted">{L(HOME.footer.rights)}</span>
        <div className="row">
          <button type="button" className="link-btn" onClick={() => setLegal(true)}>{L(HOME.footer.legal)}</button>
          <button type="button" className="link-btn" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
            {lang === "ar" ? "English" : "العربية"}
          </button>
        </div>
      </footer>
      <LegalDrawer open={legal} onClose={() => setLegal(false)} />
    </div>
  );
}

function Section({ id, title, sub, children }: { id: string; title: string; sub?: string; children: ReactNode }) {
  return (
    <section id={id} className="home-section">
      <div className="section-title"><h2>{title}</h2></div>
      {sub && <p className="muted" style={{ marginTop: -6 }}>{sub}</p>}
      {children}
    </section>
  );
}
