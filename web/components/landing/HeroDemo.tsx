"use client";

// The hero mock-up (docs/website/landing-motion.md §3): a short chat fills a product summary, once, then rests.
// Labelled as an example. With reduced motion, or when replay isn't wanted, it shows the final state at once.
import { useCallback, useEffect, useRef, useState } from "react";

import { ReplayIcon } from "@/components/Icons";
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";

const D = HOME.demo;
// step: 0 nothing · 1 typing customer · 2 assistant dots · 3 reply · 4 chip picked · 5+n rows shown · 9 ready
const ROWS = D.rows.length;

export default function HeroDemo() {
  const { lang } = useLang();
  const [typed, setTyped] = useState(0);
  const [step, setStep] = useState(0);
  const [values, setValues] = useState<string[] | null>(null);
  const timers = useRef<number[]>([]);
  const customer = D.customer[lang];

  const clear = () => { timers.current.forEach(clearTimeout); timers.current = []; };
  const at = (ms: number, fn: () => void) => { timers.current.push(window.setTimeout(fn, ms)); };

  const play = useCallback(() => {
    clear();
    setValues(null);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setTyped(customer.length);
      setStep(9);
      return;
    }
    setTyped(0);
    setStep(1);
    // Customer types (~40 ms per character), assistant thinks, replies, a chip is picked, rows fill in
    const typeEnd = 600 + customer.length * 40;
    for (let i = 1; i <= customer.length; i++) at(600 + i * 40, () => setTyped(i));
    at(Math.max(typeEnd, 2000), () => setStep(2));
    at(Math.max(typeEnd, 2000) + 600, () => setStep(3));
    at(Math.max(typeEnd, 2000) + 1400, () => setStep(4));
    for (let r = 0; r < ROWS; r++) at(Math.max(typeEnd, 2000) + 1800 + r * 500, () => setStep(5 + r));
    at(Math.max(typeEnd, 2000) + 1800 + ROWS * 500 + 300, () => setStep(9));
  }, [customer]);

  // Start once the frame is on screen and the tab is visible; restart when the language changes
  const frame = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = frame.current;
    if (!el) return;
    let started = false;
    const go = () => { if (!started && !document.hidden) { started = true; play(); } };
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) go(); }, { threshold: 0.3 });
    io.observe(el);
    const onVis = () => { if (!document.hidden && el.getBoundingClientRect().top < window.innerHeight) go(); };
    document.addEventListener("visibilitychange", onVis);
    return () => { io.disconnect(); document.removeEventListener("visibilitychange", onVis); clear(); };
  }, [play]);

  const shownRows = step >= 9 ? ROWS : Math.max(0, step - 4);
  const rowValue = (i: number) => values?.[i] ?? D.rows[i].value[lang];

  return (
    <div className="ln-demo" ref={frame}>
      <div className="ln-demo-bar">
        <span className="ln-demo-dots" aria-hidden><i /><i /><i /></span>
        <span className="ln-demo-label">{D.label[lang]}</span>
        <button type="button" className="ln-icon-btn" onClick={play} aria-label={D.replay[lang]} title={D.replay[lang]}>
          <ReplayIcon width={16} height={16} />
        </button>
      </div>
      <div className="ln-demo-body">
        <div className="ln-chat" aria-live="off">
          <div className="ln-chat-head">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/brand/mark-gold.png" alt="" width={22} height={21} />
            <span>{D.assistant[lang]}</span>
          </div>
          {typed > 0 && (
            <div className="ln-bubble me">{customer.slice(0, typed)}{step === 1 && <span className="ln-caret" />}</div>
          )}
          {step === 2 && <div className="ln-bubble them ln-typing" aria-label="…"><i /><i /><i /></div>}
          {step >= 3 && <div className="ln-bubble them ln-pop">{D.reply[lang]}</div>}
          {step >= 3 && (
            <div className="ln-chips">
              {D.chips.map((c, i) => (
                <span key={i} className={`ln-chip${step >= 4 && i === 0 ? " on" : ""}`}>{c[lang]}</span>
              ))}
            </div>
          )}
        </div>
        <div className="ln-spec">
          <div className="ln-spec-title">{D.specTitle[lang]}</div>
          {D.rows.map((r, i) => (
            <div key={i} className={`ln-spec-row${i < shownRows ? " in" : ""}${i === shownRows - 1 && step < 9 ? " flash" : ""}`}>
              <span>{r.label[lang]}</span>
              {/* At rest the values can be edited: the customer stays in control */}
              <input
                aria-label={r.label[lang]} value={i < shownRows ? rowValue(i) : ""} readOnly={step < 9}
                onChange={(e) => setValues((v) => {
                  const next = v ?? D.rows.map((x) => x.value[lang]);
                  return next.map((x, j) => (j === i ? e.target.value : x));
                })}
              />
            </div>
          ))}
          <div className={`ln-ready${step >= 9 ? " in" : ""}`}>{D.ready[lang]}</div>
          {step >= 9 && <div className="ln-edit-hint">{D.editHint[lang]}</div>}
        </div>
      </div>
    </div>
  );
}
