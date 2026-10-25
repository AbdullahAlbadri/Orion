"use client";

// One scrollable drawer for terms, privacy, refunds, restricted products and IP (docs/website/00-sitemap.md).
// The texts are being prepared with a lawyer; nothing is invented here.
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";

export default function LegalDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { lang } = useLang();
  if (!open) return null;
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={HOME.legal.title[lang]} onClick={(e) => e.stopPropagation()}>
        <div className="spread">
          <h2 style={{ margin: 0 }}>{HOME.legal.title[lang]}</h2>
          <button type="button" className="icon-btn" aria-label="close" onClick={onClose}>×</button>
        </div>
        <p className="receipt-note">{HOME.legal.note[lang]}</p>
        {HOME.legal.sections.map((s) => (
          <section key={s.en} className="board board-glass">
            <h3 style={{ margin: 0 }}>{s[lang]}</h3>
          </section>
        ))}
      </aside>
    </div>
  );
}
