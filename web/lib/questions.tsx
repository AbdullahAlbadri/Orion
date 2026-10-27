// Shared by the form and the receipt: icons, Arabic wording, cost tiers, colour swatches, error messages.
import type { ReactNode } from "react";

import {
  BoxIcon, ClockIcon, HashIcon, ImageIcon, LayersIcon, NeedleIcon, PaletteIcon, RulerIcon, ScaleIcon, ShieldIcon,
  ShirtIcon, SparkleIcon, TagIcon, TargetIcon,
} from "@/components/Icons";
import type { Question } from "./api";
import type { Lang } from "./i18n";

const ICONS: Record<string, () => ReactNode> = {
  colors: () => <PaletteIcon />, color_zones: () => <PaletteIcon />, decoration_method: () => <NeedleIcon />, decoration_placement: () => <TargetIcon />,
  artwork: () => <ImageIcon />, fabric: () => <LayersIcon />, fabric_gsm: () => <ScaleIcon />,
  size_breakdown: () => <RulerIcon />, size_standard: () => <RulerIcon />, quantity: () => <HashIcon />,
  labels: () => <TagIcon />, embellishment: () => <SparkleIcon />, dimensions: () => <RulerIcon />,
  handle_length: () => <RulerIcon />, abaya_length: () => <RulerIcon />, packaging: () => <BoxIcon />,
  needed_by: () => <ClockIcon />, sample: () => <ShieldIcon />,
};

export const iconFor = (id: string): ReactNode => (ICONS[id] ?? (() => <ShirtIcon />))();

export const questionText = (q: Question, lang: Lang) => (lang === "ar" && q.prompt_ar ? q.prompt_ar : q.prompt);
export const questionHint = (q: Question, lang: Lang) => (lang === "ar" && q.hint_ar ? q.hint_ar : q.hint);

/** The label shown for a choice; the value sent to the API stays the English choice. */
export function choiceLabel(q: Question, value: string, lang: Lang): string {
  if (lang !== "ar" || !q.choices_ar?.length) return value;
  const i = q.choices.indexOf(value);
  return i >= 0 && q.choices_ar[i] ? q.choices_ar[i] : value;
}

export function costTier(q: Question, value: string): number {
  const i = q.choices.indexOf(value);
  return i >= 0 ? q.cost_tiers?.[i] ?? 0 : 0;
}

// Swatches for the standard colour choices (other colours are shown as text)
export const COLOR_SWATCHES: Record<string, string> = {
  black: "#111111", white: "#f5f5f5", navy: "#1f2a4d", grey: "#8a8d93", beige: "#d9c7a7", olive: "#6b6b3a",
};

// The API's validation messages in Arabic (fallback: the original English)
const ERRORS_AR: [RegExp, string][] = [
  [/^This answer is required\.?$/, "هذه الإجابة مطلوبة."],
  [/^an answer is required$/, "الإجابة مطلوبة."],
  [/^must be a number$/, "يجب أن تكون رقمًا."],
  [/^must be greater than zero$/, "يجب أن تكون أكبر من صفر."],
  [/^must be one of/, "اختر أحد الخيارات."],
  [/^pick one option$/, "اختر خيارًا واحدًا."],
  [/^enter at least one size/, "أدخل مقاسًا واحدًا على الأقل مع الكمية."],
  [/^could not read/, "لم نفهم أحد المقاسات، اكتبه مثل M:50."],
  [/size must be between/, "يجب أن يكون الحجم بين 0.5 و60 سم."],
  [/outside the garment/, "الموضع خارج القطعة."],
];

export function errorText(message: string, lang: Lang): string {
  if (lang !== "ar") return message;
  return ERRORS_AR.find(([re]) => re.test(message))?.[1] ?? message;
}
