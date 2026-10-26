"use client";

// Why Orion: you on one side, Orion in the middle, many factories on the other. One gold line to you, many
// faint lines to factories, with pulses travelling along them. Any product, not one category.
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";

const FACTORIES = [[820, 60], [880, 150], [900, 250], [860, 340], [780, 410], [700, 30]] as const;
const HUB = [500, 220] as const;
const YOU = [120, 220] as const;

export default function Network() {
  const { lang } = useLang();
  const curve = (a: readonly number[], b: readonly number[]) =>
    `M${a[0]} ${a[1]} C ${(a[0] + b[0]) / 2} ${a[1]}, ${(a[0] + b[0]) / 2} ${b[1]}, ${b[0]} ${b[1]}`;
  return (
    <figure className="ln-network" data-reveal>
      <div className="ln-network-art" dir="ltr">
        <svg viewBox="0 0 1000 440" aria-hidden>
          {FACTORIES.map((f, i) => (
            <g key={i}>
              <path id={`ln-net-${i}`} className="ln-net-line" d={curve(HUB, f)} />
              <circle className="ln-net-pulse" r="3">
                <animateMotion dur={`${3 + (i % 3)}s`} begin={`${i * 0.6}s`} repeatCount="indefinite"><mpath href={`#ln-net-${i}`} /></animateMotion>
              </circle>
              <rect className="ln-net-factory" x={f[0] - 15} y={f[1] - 12} width="30" height="24" rx="3" />
              <path className="ln-net-roof" d={`M${f[0] - 15} ${f[1] - 12} l7 -7 l7 7 l8 -7 l8 7`} />
            </g>
          ))}
          <path id="ln-net-you" className="ln-net-line gold" d={curve(YOU, HUB)} />
          <circle className="ln-net-pulse gold" r="4">
            <animateMotion dur="2.6s" repeatCount="indefinite"><mpath href="#ln-net-you" /></animateMotion>
          </circle>
          <circle className="ln-net-you" cx={YOU[0]} cy={YOU[1]} r="14" />
          <circle className="ln-net-hub-ring" cx={HUB[0]} cy={HUB[1]} r="52" />
          <circle className="ln-net-hub" cx={HUB[0]} cy={HUB[1]} r="40" />
          <image href="/brand/mark-gold.png" x={HUB[0] - 20} y={HUB[1] - 19} width="40" height="38" />
        </svg>
        <span className="ln-net-label" style={{ left: "12%", top: "62%" }}>{HOME.why.you[lang]}</span>
        <span className="ln-net-label gold" style={{ left: "50%", top: "76%" }}>{lang === "ar" ? "أوريون" : "Orion"}</span>
        <span className="ln-net-label" style={{ left: "88%", top: "96%" }}>{HOME.why.factory[lang]}</span>
      </div>
      <figcaption>{HOME.why.visualCaption[lang]}</figcaption>
    </figure>
  );
}
