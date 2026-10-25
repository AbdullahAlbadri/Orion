"use client";

// FAQ (landing-motion.md §10): topic tabs with a sliding underline, accordions with the first answer open,
// arrow keys between questions, and deep links like /#faq-shipping or /#faq-customs.
import { useEffect, useLayoutEffect, useRef, useState } from "react";

import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";

const F = HOME.faq;

export default function Faq({ onPrivacy }: { onPrivacy: () => void }) {
  const { lang } = useLang();
  const [tab, setTab] = useState(F.groups[0].id);
  const [openId, setOpenId] = useState<string | null>(F.groups[0].items[0].id);
  const tabs = useRef<Record<string, HTMLButtonElement | null>>({});
  const [bar, setBar] = useState({ left: 0, width: 0 });
  const group = F.groups.find((g) => g.id === tab)!;

  useLayoutEffect(() => {
    const el = tabs.current[tab];
    if (el) setBar({ left: el.offsetLeft, width: el.offsetWidth });
  }, [tab, lang]);

  // Deep link: #faq-<group> or #faq-<question>
  useEffect(() => {
    const open = () => {
      const key = decodeURIComponent(location.hash).replace(/^#faq-/, "");
      if (!location.hash.startsWith("#faq-")) return;
      for (const g of F.groups) {
        const item = g.id === key ? g.items[0] : g.items.find((i) => i.id === key);
        if (item) {
          setTab(g.id);
          setOpenId(item.id);
          requestAnimationFrame(() => document.getElementById("faq")?.scrollIntoView({ behavior: "smooth" }));
          return;
        }
      }
    };
    open();
    window.addEventListener("hashchange", open);
    return () => window.removeEventListener("hashchange", open);
  }, []);

  const pick = (id: string) => {
    setTab(id);
    setOpenId(F.groups.find((g) => g.id === id)!.items[0].id);
  };

  const onKey = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const buttons = Array.from(e.currentTarget.closest(".ln-faq-list")!.querySelectorAll<HTMLButtonElement>(".ln-faq-q"));
    const i = buttons.indexOf(e.currentTarget);
    buttons[(i + (e.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length]?.focus();
  };

  return (
    <div className="ln-faq">
      <div className="ln-tabs" role="tablist">
        {F.groups.map((g) => (
          <button key={g.id} ref={(el) => { tabs.current[g.id] = el; }} role="tab" type="button" aria-selected={tab === g.id}
            className={tab === g.id ? "on" : ""} onClick={() => pick(g.id)}>{g.name[lang]}</button>
        ))}
        <span className="ln-tab-bar" style={{ transform: `translateX(${bar.left}px)`, width: bar.width }} />
      </div>
      <div className="ln-faq-list" key={tab}>
        {group.items.map((item) => {
          const isOpen = openId === item.id;
          return (
            <div key={item.id} id={`faq-${item.id}`} className={`ln-faq-item${isOpen ? " open" : ""}`}>
              <button type="button" className="ln-faq-q" aria-expanded={isOpen} onKeyDown={onKey}
                onClick={() => setOpenId(isOpen ? null : item.id)}>
                <span>{item.q[lang]}</span><span className="ln-plus" aria-hidden />
              </button>
              <div className="ln-faq-a"><div>
                <p>{item.a[lang]}</p>
                {group.id === "privacy" && (
                  <button type="button" className="ln-link" onClick={onPrivacy}>{F.privacyLink[lang]}</button>
                )}
              </div></div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
