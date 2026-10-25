// Static contour texture inside a board (like abatable's map panels).
import { contours, CARD_PEAKS } from "@/lib/topo";

const W = 400;
const H = 260;
const LINES = contours(W, H, CARD_PEAKS);

export default function TopoTexture() {
  return (
    <svg className="topo-texture" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice" aria-hidden>
      {LINES.map((l, i) => <path key={i} d={l.d} className={l.index ? "index" : undefined} />)}
    </svg>
  );
}
