"use client";

// Hero drawing: your idea leaves Saudi Arabia for the factory (dashed arc) and the product comes back (gold
// arc, drawn on load), with a light travelling each way. Laid out like a map in both languages: Saudi Arabia
// west (left), China east (right). Still for reduced motion.
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";

export default function RouteMap() {
  const { lang } = useLang();
  return (
    <div className="ln-routemap" dir="ltr" aria-hidden>
      <svg viewBox="0 0 1000 300" preserveAspectRatio="none">
        <path id="ln-arc-out" className="ln-arc-out" d="M120 230 C 330 -40, 670 -40, 880 200" />
        <path id="ln-arc-back" className="ln-arc-back" pathLength={1} d="M880 200 C 700 330, 320 330, 120 230" />
        <circle className="ln-traveller" r="5">
          <animateMotion dur="7s" repeatCount="indefinite"><mpath href="#ln-arc-out" /></animateMotion>
        </circle>
        <circle className="ln-traveller gold" r="4">
          <animateMotion dur="7s" begin="3.5s" repeatCount="indefinite"><mpath href="#ln-arc-back" /></animateMotion>
        </circle>
      </svg>
      <div className="ln-city" style={{ left: "12%", top: "77%" }}>
        <span className="ln-city-dot" /><b dir="auto">{HOME.hero.from[lang]}</b><small>KSA</small>
      </div>
      <div className="ln-city" style={{ left: "88%", top: "67%" }}>
        <span className="ln-city-dot" /><b dir="auto">{HOME.hero.to[lang]}</b><small>CN</small>
      </div>
    </div>
  );
}
