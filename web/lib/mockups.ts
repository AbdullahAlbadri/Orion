// Flat garment drawings for placing logos and labels. Drawn in a 400 x 440 box, seen from the front of
// the picture. cmPerUnit converts drawing units to centimetres on a size-M garment (approximate; the customer
// can type exact sizes).

export const VIEW_W = 400;
export const VIEW_H = 440;

export type View = "front" | "back";
export type PlacementKind = "logo" | "label";

export type Placement = {
  kind: PlacementKind;
  view: View;
  x: number;          // centre, fraction of VIEW_W (0-1)
  y: number;          // centre, fraction of VIEW_H (0-1)
  width_cm: number;
  height_cm: number;
};

export type Preset = { key: string; en: string; ar: string; placement: Placement };

type Mockup = {
  cmPerUnit: number;
  paths: Record<View, { body: string; details: string[] }>;
  presets: Preset[];
};

const p = (kind: PlacementKind, view: View, x: number, y: number, w: number, h: number): Placement =>
  ({ kind, view, x, y, width_cm: w, height_cm: h });

// Left chest = the wearer's left, which is the right side of a front-facing picture.
const topPresets = (neckY: number): Preset[] => [
  { key: "left_chest", en: "Left chest", ar: "يسار الصدر", placement: p("logo", "front", 0.63, 0.3, 9, 7) },
  { key: "center_chest", en: "Centre chest", ar: "وسط الصدر", placement: p("logo", "front", 0.5, 0.32, 24, 12) },
  { key: "full_front", en: "Full front", ar: "كامل الأمام", placement: p("logo", "front", 0.5, 0.5, 28, 32) },
  { key: "full_back", en: "Full back", ar: "كامل الظهر", placement: p("logo", "back", 0.5, 0.45, 30, 36) },
  { key: "back_neck", en: "Back neck", ar: "أعلى الظهر", placement: p("logo", "back", 0.5, neckY + 0.08, 8, 4) },
  { key: "neck_label", en: "Neck label", ar: "ملصق الرقبة", placement: p("label", "back", 0.5, neckY, 5, 2.5) },
];

const TEE_FRONT = "M140 40 Q200 78 260 40 L330 60 L388 150 L330 176 L302 140 L302 420 L98 420 L98 140 L70 176 L12 150 L70 60 Z";
const TEE_BACK = "M140 40 Q200 56 260 40 L330 60 L388 150 L330 176 L302 140 L302 420 L98 420 L98 140 L70 176 L12 150 L70 60 Z";
const HOODIE_BODY = "M145 58 L255 58 L322 76 L388 300 L344 314 L302 170 L302 424 L98 424 L98 170 L56 314 L12 300 L78 76 Z";

export const MOCKUPS: Record<string, Mockup> = {
  tee: {
    cmPerUnit: 0.27,
    paths: {
      front: { body: TEE_FRONT, details: ["M150 42 Q200 66 250 42"] },
      back: { body: TEE_BACK, details: [] },
    },
    presets: topPresets(0.12),
  },
  polo: {
    cmPerUnit: 0.27,
    paths: {
      front: { body: TEE_FRONT, details: ["M150 42 L182 92 L200 64 L218 92 L250 42", "M200 64 L200 140", "M196 100 h8 M196 122 h8"] },
      back: { body: TEE_BACK, details: ["M150 40 Q200 30 250 40"] },
    },
    presets: topPresets(0.12),
  },
  hoodie: {
    cmPerUnit: 0.29,
    paths: {
      front: {
        body: HOODIE_BODY,
        details: [
          "M145 60 Q150 6 200 6 Q250 6 255 60", "M168 62 Q200 92 232 62",
          "M186 80 L182 128 M214 80 L218 128", "M132 318 L268 318 L290 396 L110 396 Z",
        ],
      },
      back: { body: HOODIE_BODY, details: ["M145 60 Q150 6 200 6 Q250 6 255 60", "M150 60 Q200 120 250 60"] },
    },
    presets: [
      ...topPresets(0.17).filter((pr) => pr.key !== "full_front"),
      { key: "full_front", en: "Full front", ar: "كامل الأمام", placement: p("logo", "front", 0.5, 0.46, 26, 22) },
    ],
  },
  abaya: {
    cmPerUnit: 0.3,
    paths: {
      front: {
        body: "M160 34 Q200 58 240 34 L300 54 L388 210 L350 226 L300 140 L332 432 L68 432 L100 140 L50 226 L12 210 L100 54 Z",
        details: ["M200 52 L200 432"],
      },
      back: {
        body: "M160 34 Q200 46 240 34 L300 54 L388 210 L350 226 L300 140 L332 432 L68 432 L100 140 L50 226 L12 210 L100 54 Z",
        details: [],
      },
    },
    presets: [
      { key: "left_chest", en: "Left chest", ar: "يسار الصدر", placement: p("logo", "front", 0.62, 0.24, 7, 7) },
      { key: "back_center", en: "Back centre", ar: "وسط الظهر", placement: p("logo", "back", 0.5, 0.4, 20, 20) },
      { key: "neck_label", en: "Neck label", ar: "ملصق الرقبة", placement: p("label", "back", 0.5, 0.1, 5, 2.5) },
    ],
  },
  tote: {
    cmPerUnit: 0.173,
    paths: {
      front: { body: "M88 150 L312 150 L322 424 L78 424 Z", details: ["M140 150 Q140 30 200 30 Q260 30 260 150"] },
      back: { body: "M88 150 L312 150 L322 424 L78 424 Z", details: ["M140 150 Q140 30 200 30 Q260 30 260 150"] },
    },
    presets: [
      { key: "front_center", en: "Front centre", ar: "وسط الأمام", placement: p("logo", "front", 0.5, 0.64, 24, 24) },
      { key: "back_center", en: "Back centre", ar: "وسط الخلف", placement: p("logo", "back", 0.5, 0.64, 24, 24) },
      { key: "inside_label", en: "Small label", ar: "ملصق صغير", placement: p("label", "front", 0.5, 0.4, 5, 2.5) },
    ],
  },
};

export const mockupFor = (name?: string | null): Mockup => MOCKUPS[name ?? ""] ?? MOCKUPS.tee;
