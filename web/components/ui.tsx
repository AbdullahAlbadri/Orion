"use client";

// Small building blocks shared by the signed-in pages.
import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import { fileObjectUrl, type Bilingual } from "@/lib/api";
import { COMMON } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { mockupFor, VIEW_H, VIEW_W } from "@/lib/mockups";
import { BoxIcon, LightbulbIcon } from "./Icons";

export function PageHead({ title, sub, actions }: { title: string; sub?: string; actions?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {sub && <p className="muted">{sub}</p>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}

export function Tabs<K extends string>({ value, options, onChange, label }: {
  value: K; options: { key: K; label: string; count?: number }[]; onChange: (k: K) => void; label?: string;
}) {
  return (
    <div className="segmented" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button key={o.key} type="button" role="tab" aria-selected={value === o.key} className={value === o.key ? "on" : ""}
          onClick={() => onChange(o.key)}>
          {o.label}{o.count != null && <span className="count">{o.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Empty({ icon, title, text, action }: { icon?: ReactNode; title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="empty board board-glass">
      <span className="empty-icon">{icon ?? <BoxIcon />}</span>
      <strong>{title}</strong>
      {text && <p className="muted">{text}</p>}
      {action}
    </div>
  );
}

export function StatusChip({ status, tone }: { status: Bilingual; tone: "you" | "moving" | "done" | "closed" }) {
  const { lang } = useLang();
  return <span className={`st st-${tone}`}>{status[lang]}</span>;
}

/** "How is this calculated?": every number on the stats pages shows its method. */
export function Explain({ children }: { children: ReactNode }) {
  const { lang } = useLang();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" className="explain-btn" aria-expanded={open} onClick={() => setOpen(!open)}>
        <LightbulbIcon width={14} height={14} /> {COMMON.howCalculated[lang]}
      </button>
      {open && <p className="explain">{children}</p>}
    </>
  );
}

const MOCKUP_OF: Record<string, string> = {
  hoodie: "hoodie", oversized_tee: "tee", abaya: "abaya", tote_bag: "tote", corporate_uniform: "polo",
};

/** A product's picture: the customer's own reference photo if there is one, else Orion's drawing of it. */
export function ProductThumb({ option, picture, size = 56 }: {
  option: string | null; picture?: { order_id: string; file_id: string } | null; size?: number;
}) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!picture) return;
    let live = true;
    fileObjectUrl(picture.order_id, picture.file_id).then((u) => live && setUrl(u)).catch(() => {});
    return () => { live = false; };
  }, [picture]);

  const style = { width: size, height: size };
  // eslint-disable-next-line @next/next/no-img-element
  if (url) return <img className="thumb" src={url} alt="" style={{ ...style, objectFit: "cover" }} />;
  const name = option ? MOCKUP_OF[option] : undefined;
  if (!name) return <span className="thumb thumb-icon" style={style}><BoxIcon /></span>;
  const m = mockupFor(name);
  return (
    <span className="thumb" style={style} aria-hidden>
      <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}>
        <path d={m.paths.front.body} className="garment" />
        {m.paths.front.details.map((d) => <path key={d} d={d} className="garment-detail" />)}
      </svg>
    </span>
  );
}

export function LinkCard({ href, children, className = "" }: { href: string; children: ReactNode; className?: string }) {
  return <Link href={href} className={`link-card ${className}`}>{children}</Link>;
}
