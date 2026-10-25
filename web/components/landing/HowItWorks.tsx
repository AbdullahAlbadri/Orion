"use client";

// How it works (landing-motion.md §6): steps on one side, a sticky device frame on the other whose screen
// follows the step being read. A gold line fills with progress. Steps are buttons, so a click or the keyboard
// jumps to a screen. On phones each step shows its own screen underneath.
import { useEffect, useRef, useState } from "react";

import { CheckIcon } from "@/components/Icons";
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";

const H = HOME.how;

export default function HowItWorks() {
  const { lang } = useLang();
  const [active, setActive] = useState(0);
  const [fill, setFill] = useState(0);
  const steps = useRef<(HTMLLIElement | null)[]>([]);
  const list = useRef<HTMLOListElement>(null);

  useEffect(() => {
    // The step crossing the middle of the screen is the active one
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => {
        if (e.isIntersecting) setActive(Number((e.target as HTMLElement).dataset.step));
      }),
      { rootMargin: "-45% 0px -45% 0px" },
    );
    steps.current.forEach((el) => el && io.observe(el));
    let frame = 0;
    const onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const el = list.current;
        if (!el) return;
        const r = el.getBoundingClientRect();
        const mid = window.innerHeight / 2;
        setFill(Math.min(1, Math.max(0, (mid - r.top) / r.height)));
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => { io.disconnect(); window.removeEventListener("scroll", onScroll); if (frame) cancelAnimationFrame(frame); };
  }, []);

  const jump = (i: number) => {
    setActive(i);
    steps.current[i]?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <div className="ln-how">
      <ol className="ln-how-steps" ref={list} style={{ ["--fill" as string]: fill }}>
        {H.steps.map((s, i) => (
          <li key={i} data-step={i} ref={(el) => { steps.current[i] = el; }} className={i === active ? "on" : ""}>
            <button type="button" onClick={() => jump(i)} aria-current={i === active ? "step" : undefined}>
              <span className="ln-how-num">{i + 1}</span>
              <span>
                <strong>{s.title[lang]}</strong>
                <span className="ln-how-text">{s.text[lang]}</span>
              </span>
            </button>
            <div className="ln-how-inline"><Device><Screen index={i} /></Device></div>
          </li>
        ))}
      </ol>
      <div className="ln-how-sticky" aria-hidden>
        <Device>
          {H.steps.map((_, i) => (
            <div key={i} className={`ln-screen-layer${i === active ? " on" : ""}`}><Screen index={i} /></div>
          ))}
        </Device>
      </div>
    </div>
  );
}

function Device({ children }: { children: React.ReactNode }) {
  return (
    <div className="ln-device">
      <div className="ln-device-bar"><i /><i /><i /></div>
      <div className="ln-device-screen">{children}</div>
    </div>
  );
}

/** Clean illustrations of the real screens (TODO(decide): swap for real screenshots before launch). */
function Screen({ index }: { index: number }) {
  const { lang } = useLang();
  const S = H.screens;
  const D = HOME.demo;
  if (index === 0) {
    return (
      <div className="ln-scr">
        <div className="ln-bubble me sm">{D.customer[lang]}</div>
        <div className="ln-bubble them sm">{D.reply[lang]}</div>
        <div className="ln-chips"><span className="ln-chip on">{D.chips[0][lang]}</span><span className="ln-chip">{D.chips[1][lang]}</span></div>
        <div className="ln-scr-card">
          {D.rows.slice(0, 3).map((r, i) => <div key={i} className="ln-scr-row"><span>{r.label[lang]}</span><b>{r.value[lang]}</b></div>)}
        </div>
      </div>
    );
  }
  if (index === 1) {
    const rows: [string, string][] = [[S.logo[lang], S.logoValue[lang]], [S.sizes[lang], "S · M · L · XL"], [S.fabric[lang], D.rows[0].value[lang]]];
    return (
      <div className="ln-scr">
        <div className="ln-scr-title">{S.summary[lang]}</div>
        {[S.design, S.quantity, S.quality].map((sec, i) => (
          <div key={i} className="ln-scr-card">
            <div className="ln-scr-sec">{sec[lang]}</div>
            <div className="ln-scr-row"><span>{rows[i][0]}</span><b>{rows[i][1]}</b></div>
          </div>
        ))}
        <div className="ln-scr-btn">{S.confirm[lang]}</div>
      </div>
    );
  }
  if (index === 2) {
    return (
      <div className="ln-scr">
        <div className="ln-scr-title">{S.quote[lang]}</div>
        <div className="ln-scr-card">
          {HOME.costs.parts.map((p, i) => <div key={i} className="ln-scr-row"><span>{p.title[lang]}</span><i className="ln-bar" /></div>)}
          <div className="ln-scr-row total"><span>{HOME.costs.receipt.total[lang]}</span><i className="ln-bar gold" /></div>
        </div>
        <div className="ln-scr-actions"><span className="ln-scr-btn">{S.approve[lang]}</span><span className="ln-scr-btn ghost">{S.sample[lang]}</span></div>
      </div>
    );
  }
  return (
    <div className="ln-scr">
      <div className="ln-scr-title">{S.timeline[lang]}</div>
      <ol className="ln-scr-timeline">
        {S.stages.map((s, i) => (
          <li key={i} className={i < 3 ? "done" : i === 3 ? "now" : ""}>
            <span className="dot">{i < 3 ? <CheckIcon width={12} height={12} /> : null}</span>{s[lang]}
          </li>
        ))}
      </ol>
      <div className="ln-scr-update"><span className="ln-scr-photo" /><span className="ln-scr-photo" />{S.update[lang]}</div>
    </div>
  );
}
