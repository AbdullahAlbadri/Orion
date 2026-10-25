// "Orion suggests": the size closest to what the customer chose that factories can produce well.
// The customer decides; a suggestion is only applied when they tap it.
// Limits are common industry practice for the decoration method and area (approximate, size-M garments).
import type { Placement } from "./mockups";

export type Area = "neck" | "chest_side" | "chest_center" | "front_large" | "back";
type Limits = { minW: number; maxW: number; maxH: number };

const LOGO_LIMITS: Record<string, Partial<Record<Area, Limits>>> = {
  embroidery: {
    neck: { minW: 4, maxW: 8, maxH: 5 },
    chest_side: { minW: 5, maxW: 11, maxH: 10 },
    chest_center: { minW: 8, maxW: 25, maxH: 20 },
    front_large: { minW: 10, maxW: 25, maxH: 25 },
    back: { minW: 10, maxW: 30, maxH: 30 },
  },
  "screen print": {
    neck: { minW: 4, maxW: 10, maxH: 6 },
    chest_side: { minW: 5, maxW: 12, maxH: 12 },
    chest_center: { minW: 8, maxW: 30, maxH: 25 },
    front_large: { minW: 10, maxW: 35, maxH: 42 },
    back: { minW: 10, maxW: 35, maxH: 42 },
  },
  "DTG print": {
    neck: { minW: 4, maxW: 10, maxH: 6 },
    chest_side: { minW: 5, maxW: 12, maxH: 12 },
    chest_center: { minW: 8, maxW: 30, maxH: 25 },
    front_large: { minW: 10, maxW: 35, maxH: 40 },
    back: { minW: 10, maxW: 35, maxH: 40 },
  },
  "heat transfer": {
    neck: { minW: 3, maxW: 10, maxH: 6 },
    chest_side: { minW: 4, maxW: 12, maxH: 12 },
    chest_center: { minW: 6, maxW: 28, maxH: 25 },
    front_large: { minW: 8, maxW: 28, maxH: 28 },
    back: { minW: 8, maxW: 28, maxH: 28 },
  },
};
const LABEL_LIMITS: Limits = { minW: 3, maxW: 8, maxH: 5 };
const DEFAULT_METHOD = "screen print";

export function areaOf(p: Placement): Area {
  if (p.y < 0.2) return "neck";
  if (p.view === "back") return "back";
  if (p.y < 0.42) return Math.abs(p.x - 0.5) > 0.06 ? "chest_side" : "chest_center";
  return "front_large";
}

const round = (n: number) => Math.round(n * 2) / 2;   // nearest 0.5 cm

export type Suggestion = { width_cm: number; height_cm: number; reason: "aspect" | "too_big" | "too_small"; limits: Limits; area: Area };

/** The closest producible size, or null if the customer's size is already fine.
    `aspect` = logo width / height (from the uploaded file) keeps the logo undistorted. */
export function suggestSize(p: Placement, method: string | undefined, aspect?: number | null): Suggestion | null {
  const area = areaOf(p);
  const limits = p.kind === "label"
    ? LABEL_LIMITS
    : (LOGO_LIMITS[method ?? ""] ?? LOGO_LIMITS[DEFAULT_METHOD])[area] ?? LOGO_LIMITS[DEFAULT_METHOD][area]!;
  let w = p.width_cm;
  let h = p.height_cm;
  let reason: Suggestion["reason"] | null = null;

  // Keep the customer's width; match the logo's real proportions
  if (p.kind === "logo" && aspect && aspect > 0 && Math.abs(w / h - aspect) / aspect > 0.06) {
    h = w / aspect;
    reason = "aspect";
  }
  // Scale both sides together (no distortion) into the producible range
  const shrink = Math.min(1, limits.maxW / w, limits.maxH / h);
  const grow = w < limits.minW ? limits.minW / w : 1;
  if (shrink < 1) reason = "too_big";
  else if (grow > 1) reason = "too_small";
  const s = shrink < 1 ? shrink : grow;
  w = round(w * s);
  h = round(h * s);

  if (!reason || (Math.abs(w - p.width_cm) < 0.5 && Math.abs(h - p.height_cm) < 0.5)) return null;
  return { width_cm: w, height_cm: h, reason, limits, area };
}
