"use client";

// Page background: contour lines that drift with the mouse and scroll (parallax), a soft glow that follows
// the cursor, and a dashed route from China to Saudi Arabia. Still when the user prefers reduced motion.
import { useEffect, useMemo, useRef } from "react";

import { contours, PAGE_PEAKS } from "@/lib/topo";

const W = 1600;
const H = 1000;
// A sweeping route: east (China) to west (Saudi Arabia), drawn across the page
const ROUTE = "M1540 170 C1380 210 1290 120 1150 190 S900 330 760 300 S520 360 430 470 S230 640 70 690";

export default function TopoBackground() {
  const root = useRef<HTMLDivElement>(null);
  const lines = useMemo(() => contours(W, H, PAGE_PEAKS), []);

  useEffect(() => {
    const el = root.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let frame = 0;
    let mx = 0.5, my = 0.5;
    const apply = () => {
      frame = 0;
      el.style.setProperty("--mx", mx.toFixed(3));
      el.style.setProperty("--my", my.toFixed(3));
      el.style.setProperty("--sy", String(Math.min(window.scrollY, 2000)));
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(apply); };
    const onMove = (e: PointerEvent) => { mx = e.clientX / window.innerWidth; my = e.clientY / window.innerHeight; schedule(); };
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("scroll", schedule, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("scroll", schedule);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div ref={root} className="topo-bg" aria-hidden>
      <div className="topo-glow" />
      <svg className="topo-layer topo-far" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice">
        {lines.filter((l) => !l.index).map((l, i) => <path key={i} d={l.d} />)}
      </svg>
      <svg className="topo-layer topo-near" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice">
        {lines.filter((l) => l.index).map((l, i) => <path key={i} d={l.d} />)}
        <path className="topo-route-shadow" d={ROUTE} />
        <path className="topo-route" d={ROUTE} />
        <circle className="topo-pin" cx="1540" cy="170" r="7" />
        <circle className="topo-pin" cx="70" cy="690" r="7" />
      </svg>
    </div>
  );
}
