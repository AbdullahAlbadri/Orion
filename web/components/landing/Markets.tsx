"use client";

// Markets as a departures board: one flight per market, China to Saudi Arabia. A click opens the market's panel
// (modal on desktop, bottom sheet on phones). TODO(decide): waitlist for markets that are not open yet; no button until then.
import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { ArrowIcon, BookIcon, BoxIcon, CloseIcon, HeartIcon, LayersIcon, PlaneIcon, ShirtIcon, SparkleIcon } from "@/components/Icons";
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";

const M = HOME.markets;
const B = M.board;
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
      <div className="ln-board" data-reveal>
        <div className="ln-board-head">
          <span className="ln-board-title"><PlaneIcon className="flip-forward" width={24} height={24} /> {B.title[lang]}</span>
          <span className="ln-board-route" dir="ltr">CN → KSA</span>
        </div>
        <div className="ln-board-cols" aria-hidden>
          <span>{B.flight[lang]}</span><span>{B.market[lang]}</span><span>{B.from[lang]}</span><span>{B.to[lang]}</span><span>{B.status[lang]}</span><span />
        </div>
        {M.items.map((m, i) => (
          <button key={m.id} type="button" className="ln-board-row" style={{ ["--i" as string]: i }}
            onClick={(e) => { opener.current = e.currentTarget; setOpen(m.id); }}>
            <span className="ln-flap" dir="ltr">OR {101 + i}</span>
            <span className="ln-board-market"><strong>{m.name[lang]}</strong><small>{m.examples.map((x) => x[lang]).join(" · ")}</small></span>
            <span className="ln-board-place">{B.origin[lang]}</span>
            <span className="ln-board-place">{B.dest[lang]}</span>
            <span className={`ln-flap status${m.live ? " live" : ""}`}>{m.live && <i className="ln-blink" />}{m.live ? B.boarding[lang] : B.scheduled[lang]}</span>
            <ArrowIcon className="ln-board-more flip-forward" width={18} height={18} />
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
