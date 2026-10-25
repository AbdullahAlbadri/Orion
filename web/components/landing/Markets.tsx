"use client";

// Markets (landing-motion.md §7): six large cards; a click opens the market's panel (modal on desktop,
// bottom sheet on phones). TODO(decide): waitlist for markets that are not open yet; no button until then.
import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { ArrowIcon, BookIcon, BoxIcon, CloseIcon, HeartIcon, LayersIcon, ShirtIcon, SparkleIcon } from "@/components/Icons";
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";

const M = HOME.markets;
const ICONS: Record<string, ReactNode> = {
  shirt: <ShirtIcon />, book: <BookIcon />, layers: <LayersIcon />, sparkle: <SparkleIcon />, heart: <HeartIcon />, box: <BoxIcon />,
};

export default function Markets({ startHref }: { startHref: string }) {
  const { lang } = useLang();
  const [open, setOpen] = useState<string | null>(null);
  const selected = M.items.find((m) => m.id === open);
  const closeBtn = useRef<HTMLButtonElement>(null);
  const opener = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    closeBtn.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(null); };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      opener.current?.focus();
    };
  }, [open]);

  return (
    <>
      <div className="ln-market-grid">
        {M.items.map((m, i) => (
          <button key={m.id} type="button" className={`ln-market${m.live ? " live" : ""}`} data-reveal style={{ ["--i" as string]: i }}
            onClick={(e) => { opener.current = e.currentTarget; setOpen(m.id); }}>
            <span className="ln-market-art" aria-hidden><span className="ln-market-icon">{ICONS[m.icon]}</span></span>
            <span className="ln-market-body">
              <span className={`ln-badge${m.live ? " live" : ""}`}>{m.live && <i className="ln-pulse" />}{m.live ? M.live[lang] : M.soon[lang]}</span>
              <strong>{m.name[lang]}</strong>
              <span className="ln-market-examples">{m.examples.map((x) => x[lang]).join(" · ")}</span>
              <span className="ln-market-more">{M.more[lang]} <ArrowIcon className="flip-forward" width={16} height={16} /></span>
            </span>
          </button>
        ))}
      </div>

      {selected && (
        <div className="ln-modal-backdrop" onClick={() => setOpen(null)}>
          <div className="ln-modal" role="dialog" aria-modal="true" aria-label={selected.name[lang]} onClick={(e) => e.stopPropagation()}>
            <div className="ln-modal-head">
              <span className="ln-market-icon">{ICONS[selected.icon]}</span>
              <h3>{selected.name[lang]}</h3>
              <button ref={closeBtn} type="button" className="ln-icon-btn" onClick={() => setOpen(null)} aria-label={HOME.nav.close[lang]}>
                <CloseIcon width={18} height={18} />
              </button>
            </div>
            <span className={`ln-badge${selected.live ? " live" : ""}`}>
              {selected.live && <i className="ln-pulse" />}{selected.live ? M.live[lang] : M.soon[lang]}
            </span>
            <div className="ln-modal-cols">
              <div><div className="ln-kicker">{M.options[lang]}</div><p>{selected.options[lang]}</p></div>
              <div><div className="ln-kicker">{M.asked[lang]}</div><p>{selected.asked[lang]}</p></div>
            </div>
            {selected.live
              ? <Link href={startHref} className="ln-btn">{M.startHere[lang]} <ArrowIcon className="flip-forward" width={18} height={18} /></Link>
              : <p className="ln-muted">{M.soonNote[lang]}</p>}
          </div>
        </div>
      )}
    </>
  );
}
