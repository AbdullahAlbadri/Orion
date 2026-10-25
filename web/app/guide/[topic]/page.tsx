"use client";

// A short guide for one order question (opened from the info icon on the question, in a new tab so the
// customer's unsaved form stays as it is).
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { InfoIcon } from "@/components/Icons";
import { PageHead } from "@/components/ui";
import { type T } from "@/lib/copy";
import { GUIDES, guideImage } from "@/lib/guides";
import { useLang } from "@/lib/i18n";

const MORE = { ar: "أدلة أخرى", en: "More guides" };
const MISSING = { ar: "لا يوجد دليل بهذا الاسم.", en: "There is no guide with this name." };

/** The option's photo; options without one show none. */
function GuidePhoto({ src, alt }: { src: string; alt: string }) {
  const [missing, setMissing] = useState(false);
  const img = useRef<HTMLImageElement>(null);
  // A photo that failed before the page became interactive never fires onError: check once on mount
  useEffect(() => {
    if (img.current?.complete && img.current.naturalWidth === 0) setMissing(true);
  }, []);
  if (missing) return null;
  return (
    <figure className="guide-figure">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img ref={img} className="guide-photo" src={src} alt={alt} loading="lazy" onError={() => setMissing(true)} />
    </figure>
  );
}

export default function GuidePage() {
  const { lang } = useLang();
  const L = (x: T) => x[lang];
  const topic = String(useParams().topic ?? "");
  const guide = GUIDES[topic];
  if (!guide) return <p className="muted">{MISSING[lang]}</p>;

  return (
    <>
      <PageHead title={L(guide.title)} sub={L(guide.intro)} />
      <div className="guide-grid">
        {guide.items.map((item) => (
          <section key={item.name.en} className="board board-glass guide-item">
            <GuidePhoto src={guideImage(topic, item.name.en)} alt={L(item.name)} />
            <h2>{L(item.name)}</h2>
            <p className="muted">{L(item.text)}</p>
          </section>
        ))}
      </div>
      {guide.tip && <p className="note section-gap"><InfoIcon width={16} height={16} /> {L(guide.tip)}</p>}
      <section className="section-gap">
        <div className="section-title"><h2>{MORE[lang]}</h2></div>
        <div className="chips">
          {Object.entries(GUIDES).filter(([key]) => key !== topic).map(([key, g]) => (
            <Link key={key} href={`/guide/${key}`} className="chip">{L(g.title)}</Link>
          ))}
        </div>
      </section>
    </>
  );
}
