"use client";

// Hero drawing: an orbit. Your idea leaves Saudi Arabia for the factory along the far side (dashed) and the
// product comes back along the near side (gold, drawn on load), with a light
// travelling each way. Laid out like a map in both languages: Saudi Arabia west (left), China east (right).
// The orbit is tilted -6deg, so the cities sit where its ends land. Still for reduced motion.
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";

const TILT = "rotate(-6 500 150)";

export default function RouteMap() {
  const { lang } = useLang();
  return (
    <div className="ln-routemap ln-orbit" dir="ltr" aria-hidden>
      <svg viewBox="0 0 1000 300" preserveAspectRatio="none">
        <g transform={TILT}>
          <ellipse className="ln-orbit-ring" cx="500" cy="150" rx="470" ry="140" />
          <path id="ln-arc-out" className="ln-arc-out" d="M120 150 A380 110 0 0 1 880 150" />
          <circle className="ln-traveller" r="5">
            <animateMotion dur="7s" repeatCount="indefinite"><mpath href="#ln-arc-out" /></animateMotion>
          </circle>
          <path id="ln-arc-back" className="ln-arc-back" pathLength={1} d="M880 150 A380 110 0 0 1 120 150" />
          <circle className="ln-traveller gold" r="4">
            <animateMotion dur="7s" begin="3.5s" repeatCount="indefinite"><mpath href="#ln-arc-back" /></animateMotion>
          </circle>
        </g>
      </svg>
      <div className="ln-city west" style={{ left: "12.2%", top: "63.2%" }}>
        <span className="ln-city-dot" /><span className="ln-city-label"><b dir="auto">{HOME.hero.from[lang]}</b><small>KSA</small></span>
      </div>
      <div className="ln-city east" style={{ left: "87.8%", top: "36.8%" }}>
        <span className="ln-city-dot" /><span className="ln-city-label"><b dir="auto">{HOME.hero.to[lang]}</b><small>CN</small></span>
      </div>
    </div>
  );
}
