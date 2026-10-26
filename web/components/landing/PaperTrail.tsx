"use client";

// How it works as the order's paper trail: a different document at each stop (the conversation, the spec
// sheet, the quote, the shipping label), the same order code on each, linked by a route that draws itself as
// you scroll. Each document is stamped as you reach it. Illustrations only: no prices.
import { useEffect, useRef, type ReactNode } from "react";

import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";

const H = HOME.how;
const D = HOME.demo;
const TR = H.trail;
const CODE = "ORN-0042";

export default function PaperTrail() {
  const { lang } = useLang();
  const L = (x: { ar: string; en: string }) => x[lang];
  const track = useRef<HTMLDivElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const base = useRef<SVGPathElement>(null);
  const drawn = useRef<SVGPathElement>(null);

  useEffect(() => {
    const t = track.current, s = svg.current, b = base.current, d = drawn.current;
    if (!t || !s || !b || !d) return;
    const stops = Array.from(t.querySelectorAll<HTMLElement>(".ln-stop"));
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let len = 0, frame = 0;

    // A curve from the top, through a point beside each document, down to the door
    const layout = () => {
      const box = t.getBoundingClientRect();
      s.setAttribute("viewBox", `0 0 ${box.width} ${box.height}`);
      const pts = stops.map((stop) => {
        const r = stop.getBoundingClientRect();
        const onLeft = r.left - box.left < box.width / 2;
        return [onLeft ? r.right - box.left + 56 : r.left - box.left - 56, r.top - box.top + r.height / 2];
      });
      let path = `M ${box.width / 2} 0`;
      pts.forEach(([x, y], i) => {
        const [px, py] = i ? pts[i - 1] : [box.width / 2, 0];
        path += ` C ${px} ${(py + y) / 2}, ${x} ${(py + y) / 2}, ${x} ${y}`;
      });
      // ...and ends on top of the door's pin
      const [lx, ly] = pts[pts.length - 1];
      const pin = t.querySelector<HTMLElement>(".ln-dest-pin")!.getBoundingClientRect();
      const ex = pin.left - box.left + pin.width / 2, ey = pin.top - box.top - 2;
      path += ` C ${lx} ${(ly + ey) / 2}, ${ex} ${(ly + ey) / 2}, ${ex} ${ey}`;
      b.setAttribute("d", path);
      d.setAttribute("d", path);
      len = d.getTotalLength();
      d.style.strokeDasharray = `${len}`;
      update();
    };
    const update = () => {
      frame = 0;
      const box = t.getBoundingClientRect();
      const p = still ? 1 : Math.min(1, Math.max(0, (window.innerHeight * 0.62 - box.top) / box.height));
      d.style.strokeDashoffset = `${len * (1 - p)}`;
      for (const stop of stops) {
        const r = stop.getBoundingClientRect();
        if (still || r.top + r.height / 2 < window.innerHeight * 0.62) stop.classList.add("in");
      }
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
    const ro = new ResizeObserver(layout);
    ro.observe(t);
    document.fonts?.ready.then(layout);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => { ro.disconnect(); window.removeEventListener("scroll", onScroll); if (frame) cancelAnimationFrame(frame); };
  }, [lang]);

  const top = (n: number, right: ReactNode) => (
    <div className="ln-doc-top"><span>{CODE} · {L(TR.stop)} {String(n).padStart(2, "0")}</span><b>{right}</b></div>
  );
  const body = (i: number) => (
    <><h3>{L(H.steps[i].title)}</h3><p>{L(H.steps[i].text)}</p></>
  );
  const stamp = (label: { ar: string; en: string }) => <div className="ln-stamp" aria-hidden>{L(label)}</div>;

  return (
    <div className="ln-trail" ref={track}>
      <svg className="ln-trail-line" ref={svg} aria-hidden><path className="base" ref={base} /><path className="drawn" ref={drawn} /></svg>
      <ol className="ln-stops">
        <li className="ln-stop">
          <div className="ln-doc ln-doc-chat" style={{ ["--r" as string]: "-1.4deg" }}>
            {top(1, "ORION")}
            <div className="ln-bubbles">
              <div className="ln-b me">{L(D.customer)}</div>
              <div className="ln-b ai"><small>{L(D.assistant)}</small>{L(D.reply)}</div>
              <div className="ln-chips">{D.chips.map((c, i) => <span key={i} className={i === 0 ? "on" : ""}>{L(c)}</span>)}</div>
            </div>
            {body(0)}
            {stamp(TR.done)}
          </div>
        </li>
        <li className="ln-stop">
          <div className="ln-doc ln-doc-sheet" style={{ ["--r" as string]: "1.2deg" }}>
            {top(2, L(D.specTitle))}
            <dl>
              {D.rows.map((r, i) => (
                <div key={i}><span className="ln-tick">✓</span><dt>{L(r.label)}</dt><dd>{L(r.value)}</dd></div>
              ))}
            </dl>
            {body(1)}
            {stamp(TR.done)}
          </div>
        </li>
        <li className="ln-stop">
          <div className="ln-doc ln-doc-receipt" style={{ ["--r" as string]: "-0.8deg" }}>
            {top(3, L(H.screens.quote))}
            <div className="ln-receipt-rows">
              <div><span>{L(TR.product)}</span><i /><span>{L(TR.productValue)}</span></div>
              <div><span>{L(TR.sampleRow)}</span><i /><span>{L(TR.sampleValue)}</span></div>
              <div><span>{L(TR.status)}</span><i /><span>{L(TR.waiting)}</span></div>
            </div>
            <div className="ln-receipt-choices"><span>{L(H.screens.approve)}</span><span>{L(H.screens.sample)}</span></div>
            {body(2)}
            {stamp(TR.approved)}
          </div>
        </li>
        <li className="ln-stop">
          <div className="ln-polaroid" aria-hidden><div className="ln-polaroid-photo" /><span>{L(H.screens.update)}</span></div>
          <div className="ln-doc ln-doc-label" style={{ ["--r" as string]: "1.6deg" }}>
            {top(4, "ORION")}
            <div className="ln-fromto">
              <div><small>{L(TR.from)}</small><span>{L(TR.factory)}</span></div>
              <div><small>{L(TR.to)}</small><span>{L(TR.door)}</span></div>
            </div>
            {body(3)}
            <div className="ln-barcode" aria-hidden />
            {stamp(TR.onTheWay)}
          </div>
        </li>
      </ol>
      <div className="ln-dest"><span className="ln-dest-pin" aria-hidden /><b>{L(TR.door)}</b></div>
    </div>
  );
}
