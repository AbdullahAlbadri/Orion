// Topographic contour lines (like a terrain map), generated once from a fixed seed so every render matches.

type Peak = { cx: number; cy: number; rings: number; base: number; gap: number; phase: number };

function ring(cx: number, cy: number, r: number, phase: number, wobble: number): string {
  const steps = 72;
  let d = "";
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * Math.PI * 2;
    const rr = r + wobble * (Math.sin(3 * t + phase) * 0.6 + Math.sin(5 * t + phase * 1.7) * 0.3 + Math.sin(2 * t - phase) * 0.4);
    const x = cx + rr * Math.cos(t) * 1.25;   // a little wider than tall
    const y = cy + rr * Math.sin(t);
    d += `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)} `;
  }
  return d + "Z";
}

/** Contour rings around a few "peaks" in a w x h box. Every 4th ring is an index contour (drawn bolder). */
export function contours(w: number, h: number, peaks: Peak[]): { d: string; index: boolean }[] {
  const out: { d: string; index: boolean }[] = [];
  for (const p of peaks) {
    for (let k = 0; k < p.rings; k++) {
      const r = p.base + k * p.gap;
      out.push({ d: ring(p.cx * w, p.cy * h, r, p.phase + k * 0.18, 6 + k * 2.2), index: k % 4 === 3 });
    }
  }
  return out;
}

export const PAGE_PEAKS: Peak[] = [
  { cx: 0.18, cy: 0.22, rings: 14, base: 30, gap: 26, phase: 0.4 },
  { cx: 0.82, cy: 0.7, rings: 16, base: 24, gap: 28, phase: 2.1 },
  { cx: 0.62, cy: 0.12, rings: 7, base: 20, gap: 22, phase: 4.0 },
  { cx: 0.35, cy: 0.88, rings: 9, base: 26, gap: 24, phase: 5.2 },
];

export const CARD_PEAKS: Peak[] = [
  { cx: 0.75, cy: 0.35, rings: 9, base: 14, gap: 14, phase: 1.2 },
  { cx: 0.15, cy: 0.95, rings: 7, base: 12, gap: 15, phase: 3.3 },
];
