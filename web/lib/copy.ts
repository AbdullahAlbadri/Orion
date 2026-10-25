// Shared bilingual text for the signed-in pages. Page-specific wording lives at the top of each page file.
// Rule (docs/website): no invented prices, statistics, timelines or legal text; undecided items stay out.
import type { Lang } from "./i18n";

export type T = Record<Lang, string>;
export const t = (ar: string, en: string): T => ({ ar, en });

export const NAV = {
  overview: t("نظرة عامة", "Overview"),
  orders: t("الطلبات", "Orders"),
  shipments: t("الشحنات", "Shipments"),
  products: t("منتجاتي", "My products"),
  payments: t("المدفوعات والمستندات", "Payments & documents"),
  stats: t("الإحصاءات", "Stats"),
  settings: t("الإعدادات", "Settings"),
  messages: t("الرسائل", "Messages"),
  help: t("المساعدة", "Help"),
  business: t("ملف النشاط التجاري", "Business profile"),
  signOut: t("تسجيل الخروج", "Sign out"),
  newOrder: t("طلب جديد", "New order"),
  more: t("المزيد", "More"),
  account: t("الحساب", "Account"),
  seeAll: t("عرض الكل", "See all"),
  noUpdates: t("لا تحديثات بعد.", "No updates yet."),
  hello: t("أهلًا", "Hello"),
};

export const COMMON = {
  loading: t("جارٍ التحميل…", "Loading…"),
  error: t("حدث خطأ. حاول مرة أخرى.", "Something went wrong. Please try again."),
  save: t("حفظ", "Save"),
  saved: t("تم الحفظ", "Saved"),
  saving: t("جارٍ الحفظ…", "Saving…"),
  cancel: t("إلغاء", "Cancel"),
  edit: t("تعديل", "Edit"),
  remove: t("حذف", "Remove"),
  open: t("فتح", "Open"),
  search: t("بحث", "Search"),
  all: t("الكل", "All"),
  pieces: t("قطعة", "pcs"),
  howCalculated: t("كيف يُحسب هذا؟", "How is this calculated?"),
  continueDraft: t("أكمل المسودة", "Continue draft"),
  reorder: t("إعادة الطلب", "Reorder"),
  startFirst: t("ابدأ طلبك الأول", "Start your first order"),
  optional: t("اختياري", "optional"),
  back: t("رجوع", "Back"),
  next: t("التالي", "Next"),
  later: t("لاحقًا", "Later"),
  notYet: t("لم يتوفر بعد", "Not available yet"),
};

/** Western digits for figures (the Arabic-Indic zero looks like a dot next to Arabic text). */
export const num = (n: number) => n.toLocaleString("en-GB");

export function duration(hours: number, lang: Lang): string {
  if (hours >= 48) return `${num(Math.round(hours / 24))} ${lang === "ar" ? "يوم" : "days"}`;
  if (hours >= 1) return `${num(Math.round(hours * 10) / 10)} ${lang === "ar" ? "ساعة" : "h"}`;
  return `${num(Math.max(1, Math.round(hours * 60)))} ${lang === "ar" ? "دقيقة" : "min"}`;
}

export type Calendar = "gregorian" | "hijri" | "both";

/** A date in the customer's chosen calendar (Settings): Gregorian, Hijri (Umm al-Qura) or both. */
export function formatDate(iso: string | null | undefined, lang: Lang, calendar: Calendar = "gregorian", withTime = false): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric", numberingSystem: "latn",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}) };
  const base = lang === "ar" ? "ar-SA" : "en-GB";
  const gregorian = d.toLocaleString(`${base}-u-ca-gregory`, opts);
  const hijri = d.toLocaleString(`${base}-u-ca-islamic-umalqura`, opts);
  if (calendar === "hijri") return hijri;
  if (calendar === "both") return `${gregorian} · ${hijri}`;
  return gregorian;
}

/** "3 hours ago" style, for update lists. */
export function ago(iso: string, lang: Lang): string {
  const secs = (Date.now() - new Date(iso).getTime()) / 1000;
  const rtf = new Intl.RelativeTimeFormat(lang === "ar" ? "ar" : "en", { numeric: "auto" });
  if (secs < 60) return rtf.format(0, "second");
  if (secs < 3600) return rtf.format(-Math.round(secs / 60), "minute");
  if (secs < 86400) return rtf.format(-Math.round(secs / 3600), "hour");
  return rtf.format(-Math.round(secs / 86400), "day");
}
