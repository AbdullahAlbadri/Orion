"use client";

// Landing page, "the journey" design: your idea leaves for the factory and your product comes back to your door.
// Each section is a piece of that route: the route map, the factory network, the order's paper trail, parcels,
// an invoice, a letter from the team, and the door. Everything is still with reduced motion.
// Left out until the team decides: contact (WhatsApp/email), team portraits, waitlist, payment and sample FAQs.
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ArrowIcon, CheckIcon, CloseIcon, GlobeIcon, LockIcon, MenuIcon, UsersIcon } from "@/components/Icons";
import Faq from "@/components/landing/Faq";
import Markets from "@/components/landing/Markets";
import Network from "@/components/landing/Network";
import PaperTrail from "@/components/landing/PaperTrail";
import RouteMap from "@/components/landing/RouteMap";
import LegalDrawer from "@/components/LegalDrawer";
import { useAuth } from "@/lib/auth";
import { HOME, type T } from "@/lib/home";
import { useLang } from "@/lib/i18n";
import { thDisplay, thSans } from "./fonts";
import "./landing.css";

const SECTIONS = [
  { id: "how", label: HOME.nav.how },
  { id: "markets", label: HOME.nav.markets },
  { id: "costs", label: HOME.nav.costs },
  { id: "faq", label: HOME.nav.faq },
];

export default function Landing() {
  const { lang, setLang } = useLang();
  const { user } = useAuth();
  const [legal, setLegal] = useState(false);
  const L = (x: T) => x[lang];
  const startHref = user ? "/orders/new" : "/start";
  const root = useRef<HTMLDivElement>(null);
  useReveal(root, lang);

  return (
    <div className={`ln ${thSans.variable} ${thDisplay.variable}`} ref={root}>
      <a href="#main" className="ln-skip">{L(HOME.nav.skip)}</a>
      <Nav startHref={startHref} signedIn={!!user} />

      <section className="ln-hero" id="top">
        <div className="ln-wrap">
          <p className="ln-kicker ln-enter">{L(HOME.hero.kicker)}</p>
          <h1 className="ln-hero-title" key={lang}>
            {L(HOME.hero.words).split(" ").map((w, i) => (
              <span key={i} className="ln-word" style={{ ["--w" as string]: i }}>
                <span className={w.replace(/[.,،]/g, "") === L(HOME.hero.accent) ? "ln-accent" : undefined}>{w}</span>{" "}
              </span>
            ))}
          </h1>
          <p className="ln-hero-sub ln-enter" style={{ ["--d" as string]: 1 }}>{L(HOME.hero.sub)}</p>
          <div className="ln-row ln-enter" style={{ ["--d" as string]: 2 }}>
            <Link href={startHref} className="ln-btn">{L(HOME.nav.start)} <ArrowIcon className="ln-arrow" width={18} height={18} /></Link>
            <a href="#how" className="ln-btn-line">{L(HOME.hero.secondary)}</a>
          </div>
          <RouteMap />
        </div>
      </section>

      <ProductStrip />

      <main id="main">
        <section className="ln-section" id="why">
          <div className="ln-wrap">
            <SectionHead num={HOME.why.num} title={L(HOME.why.title)} />
            <div className="ln-why">
              <Network />
              <ul className="ln-points">
                {HOME.why.points.map((p, i) => (
                  <li key={i} data-reveal style={{ ["--i" as string]: i }}>
                    <span className="ln-point-dot" aria-hidden />
                    <div><h3>{L(p.title)}</h3><p>{L(p.text)}</p></div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        <section className="ln-section" id="how">
          <div className="ln-wrap">
            <SectionHead num={HOME.how.num} title={L(HOME.how.title)} aside={L(HOME.how.trail.code)} />
            <PaperTrail />
          </div>
        </section>

        <section className="ln-section" id="markets">
          <div className="ln-wrap">
            <SectionHead num={HOME.markets.num} title={L(HOME.markets.title)} />
            <Markets startHref={startHref} />
          </div>
        </section>

        <section className="ln-section" id="costs">
          <div className="ln-wrap ln-costs">
            <div>
              <SectionHead num={HOME.costs.num} title={L(HOME.costs.title)} />
              <ul className="ln-promises">
                {HOME.costs.promises.map((p, i) => (
                  <li key={i} data-reveal style={{ ["--i" as string]: i }}><CheckIcon width={18} height={18} /> {L(p)}</li>
                ))}
              </ul>
            </div>
            <figure className="ln-invoice-wrap" data-reveal>
              <div className="ln-invoice">
                <div className="ln-doc-top"><span>ORN-0042 · INVOICE</span><b>{L(HOME.costs.receipt.title)}</b></div>
                {HOME.costs.parts.map((p, i) => (
                  <div key={i} className="ln-invoice-row" style={{ ["--i" as string]: i }}>
                    <div><strong>{L(p.title)}</strong><small>{L(p.text)}</small></div>
                    <i className="ln-leader" /><span className="ln-amount" aria-hidden>—</span>
                  </div>
                ))}
                <div className="ln-invoice-row total">
                  <div><strong>{L(HOME.costs.receipt.total)}</strong></div><i className="ln-leader" /><span className="ln-amount gold" aria-hidden>—</span>
                </div>
              </div>
              <figcaption>{L(HOME.costs.receipt.caption)}</figcaption>
            </figure>
          </div>
        </section>

        <section className="ln-section" id="people">
          <div className="ln-wrap">
            <SectionHead num={HOME.people.num} title={L(HOME.people.title)} />
            <div className="ln-letter" data-reveal>
              {HOME.people.commitments.map((c, i) => (
                <div key={i} className="ln-commit" style={{ ["--i" as string]: i }}>
                  <span className="ln-seal">{{ lock: <LockIcon />, check: <CheckIcon />, people: <UsersIcon /> }[c.icon]}</span>
                  <div><h3>{L(c.title)}</h3><p>{L(c.text)}</p></div>
                </div>
              ))}
              <p className="ln-signature">{lang === "ar" ? "— فريق أوريون" : "— The Orion team"}</p>
            </div>
          </div>
        </section>

        <section className="ln-section" id="faq">
          <div className="ln-wrap ln-narrow">
            <SectionHead num={HOME.faq.num} title={L(HOME.faq.title)} />
            <Faq onPrivacy={() => setLegal(true)} />
          </div>
        </section>

        <section className="ln-closing" id="closing">
          <div className="ln-wrap">
            <span className="ln-dest-pin big" aria-hidden />
            <h2 className="ln-closing-lines" data-reveal="lines" key={lang}>
              {HOME.closing.lines.map((l, i) => (
                <span key={i} className="ln-line" style={{ ["--i" as string]: i }}><span>{L(l)}</span></span>
              ))}
            </h2>
            <Link href={startHref} className="ln-btn">{L(HOME.nav.start)} <ArrowIcon className="ln-arrow" width={18} height={18} /></Link>
          </div>
        </section>
      </main>

      <footer className="ln-footer">
        <div className="ln-wrap ln-footer-row">
          <Link href="/" className="ln-logo" aria-label="Orion">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/mark-gold.png" alt="" width={30} height={28} />
            <span>{lang === "ar" ? "أوريون" : "Orion"}</span>
          </Link>
          <nav className="ln-footer-links">
            {SECTIONS.map((s) => <a key={s.id} href={`#${s.id}`}>{L(s.label)}</a>)}
            <button type="button" onClick={() => setLegal(true)}>{L(HOME.footer.legal)}</button>
            <button type="button" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>{lang === "ar" ? "English" : "العربية"}</button>
          </nav>
          <span className="ln-muted">{L(HOME.footer.rights)}</span>
        </div>
      </footer>

      <MobileBar startHref={startHref} />
      <LegalDrawer open={legal} onClose={() => setLegal(false)} />
    </div>
  );
}

function SectionHead({ num, title, aside }: { num: string; title: string; aside?: string }) {
  const { lang } = useLang();
  // Section numbers as route stops; Arabic-Indic digits in Arabic
  const n = lang === "ar" ? Number(num).toLocaleString("ar-EG", { minimumIntegerDigits: 2 }) : num;
  return (
    <div className="ln-head" data-reveal>
      <span className="ln-num">{n}</span>
      <h2>{title}</h2>
      {aside && <span className="ln-head-aside">{aside}</span>}
    </div>
  );
}

/** Fade-up reveals: elements with data-reveal get "in" once, when they enter the screen. */
function useReveal(root: React.RefObject<HTMLDivElement | null>, lang: string) {
  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      }),
      { rootMargin: "0px 0px -10% 0px" },
    );
    el.querySelectorAll("[data-reveal]:not(.in)").forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, [root, lang]);
}

function Nav({ startHref, signedIn }: { startHref: string; signedIn: boolean }) {
  const { lang, setLang } = useLang();
  const L = (x: T) => x[lang];
  const [solid, setSolid] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [progress, setProgress] = useState(0);
  const [active, setActive] = useState<string | null>(null);
  const [menu, setMenu] = useState(false);
  const links = useRef<Record<string, HTMLAnchorElement | null>>({});
  const [bar, setBar] = useState<{ left: number; width: number } | null>(null);

  useEffect(() => {
    let last = window.scrollY;
    let frame = 0;
    const onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const y = window.scrollY;
        setSolid(y > 40);
        setHidden(y > 120 && y > last + 4 ? true : y < last - 4 ? false : (h) => h);
        last = y;
        const max = document.documentElement.scrollHeight - window.innerHeight;
        setProgress(max > 0 ? y / max : 0);
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) setActive(e.target.id); }),
      { rootMargin: "-40% 0px -55% 0px" },
    );
    for (const id of ["top", "why", ...SECTIONS.map((s) => s.id), "people", "closing"]) {
      const node = document.getElementById(id);
      if (node) io.observe(node);
    }
    return () => { window.removeEventListener("scroll", onScroll); io.disconnect(); if (frame) cancelAnimationFrame(frame); };
  }, []);

  useEffect(() => {
    const a = active ? links.current[active] : null;
    setBar(a ? { left: a.offsetLeft, width: a.offsetWidth } : null);
  }, [active, lang]);

  useEffect(() => {
    if (!menu) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setMenu(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [menu]);

  return (
    <>
      <header className={`ln-nav${solid ? " solid" : ""}${hidden && !menu ? " away" : ""}`}>
        <div className="ln-wrap ln-nav-row">
          <Link href="/" className="ln-logo" aria-label="Orion">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/mark-gold.png" alt="" width={30} height={28} />
            <span>{lang === "ar" ? "أوريون" : "Orion"}</span>
          </Link>
          <nav className="ln-nav-links">
            {SECTIONS.map((s) => (
              <a key={s.id} href={`#${s.id}`} ref={(el) => { links.current[s.id] = el; }}
                className={active === s.id ? "on" : ""}>{L(s.label)}</a>
            ))}
            {bar && <span className="ln-nav-bar" style={{ transform: `translateX(${bar.left}px)`, width: bar.width }} />}
          </nav>
          <div className="ln-row ln-nav-actions">
            <button type="button" className="ln-btn-text" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
              <GlobeIcon width={16} height={16} /> {lang === "ar" ? "English" : "العربية"}
            </button>
            <Link href={signedIn ? "/dashboard" : "/start"} className="ln-btn-text ln-hide-sm">
              {L(signedIn ? HOME.nav.dashboard : HOME.nav.signIn)}
            </Link>
            <Link href={startHref} className="ln-btn sm">{L(HOME.nav.start)}</Link>
            <button type="button" className="ln-icon-btn ln-menu-btn" onClick={() => setMenu(true)} aria-label={L(HOME.nav.menu)}>
              <MenuIcon width={20} height={20} />
            </button>
          </div>
        </div>
        <span className="ln-progress" style={{ transform: `scaleX(${progress})` }} />
      </header>

      <div className={`ln-sheet-backdrop${menu ? " open" : ""}`} onClick={() => setMenu(false)} aria-hidden={!menu}>
        <aside className="ln-sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label={L(HOME.nav.menu)}>
          <button type="button" className="ln-icon-btn" onClick={() => setMenu(false)} aria-label={L(HOME.nav.close)}>
            <CloseIcon width={20} height={20} />
          </button>
          {SECTIONS.map((s, i) => (
            <a key={s.id} href={`#${s.id}`} style={{ ["--i" as string]: i }} onClick={() => setMenu(false)}>{L(s.label)}</a>
          ))}
          <Link href={signedIn ? "/dashboard" : "/start"} style={{ ["--i" as string]: SECTIONS.length }}>
            {L(signedIn ? HOME.nav.dashboard : HOME.nav.signIn)}
          </Link>
        </aside>
      </div>
    </>
  );
}

function ProductStrip() {
  const { lang } = useLang();
  const items = [...HOME.strip, ...HOME.strip];
  return (
    <div className="ln-strip" aria-label={HOME.strip.map((s) => s[lang]).join("، ")}>
      <div className="ln-strip-track" aria-hidden>
        {[0, 1].map((copy) => (
          <div key={copy} className="ln-strip-set">
            {items.map((s, i) => <span key={i}>{s[lang]}<i>✦</i></span>)}
          </div>
        ))}
      </div>
    </div>
  );
}

function MobileBar({ startHref }: { startHref: string }) {
  const { lang } = useLang();
  const [show, setShow] = useState(false);
  useEffect(() => {
    const hero = document.getElementById("top");
    const closing = document.getElementById("closing");
    let heroGone = false, nearEnd = false;
    const update = () => setShow(heroGone && !nearEnd);
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.target === hero) heroGone = !e.isIntersecting;
      if (e.target === closing) nearEnd = e.isIntersecting;
      update();
    }));
    if (hero) io.observe(hero);
    if (closing) io.observe(closing);
    return () => io.disconnect();
  }, []);
  return (
    <div className={`ln-mobile-bar${show ? " in" : ""}`} aria-hidden={!show}>
      <Link href={startHref} className="ln-btn" tabIndex={show ? 0 : -1}>{HOME.nav.start[lang]}</Link>
    </div>
  );
}
