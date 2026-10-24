"use client";

// Arabic by default (right-to-left), with an English switch. Choice is remembered on this device.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

export type Lang = "ar" | "en";

const en = {
  appName: "Orion",
  tagline: "Your products, made by the right factory. We handle the rest.",
  loginTitle: "Log in or create an account",
  email: "Email",
  sendCode: "Send me a code",
  codeSent: "We sent a 6-digit code to your email.",
  code: "Code",
  verify: "Log in",
  wrongCode: "Wrong or expired code.",
  tooMany: "Too many codes requested. Try again in an hour.",
  or: "or",
  verifying: "Logging you in…",
  logout: "Log out",
  myOrders: "My orders",
  newOrder: "Start a new order",
  noOrders: "No orders yet. Tell us what you want to make.",
  thinking: "Orion is thinking…",
  send: "Send",
  typeMessage: "Write your answer…",
  submit: "Continue",
  optional: "optional",
  summary: "Your product summary",
  confirm: "Confirm and send to factories",
  requestChanges: "I want to change something",
  changesPlaceholder: "What should we change?",
  sendChanges: "Send changes",
  waitingTitle: "We're on it",
  waitingText: "We are talking to manufacturers about your product. We'll notify you as soon as there is news.",
  size: "Size",
  qty: "Pieces",
  addSize: "Add size",
  total: "Total",
  loading: "Loading…",
  error: "Something went wrong. Please try again.",
  back: "Back",
  switchLang: "العربية",
  orderTitle: "Order",
  status: "Status",
  updated: "Updated",
  pieces: "pcs",
};

const ar: typeof en = {
  appName: "أوريون",
  tagline: "منتجاتك يصنعها المصنع المناسب، ونحن نتولى الباقي.",
  loginTitle: "سجّل الدخول أو أنشئ حسابًا",
  email: "البريد الإلكتروني",
  sendCode: "أرسل لي الرمز",
  codeSent: "أرسلنا رمزًا من 6 أرقام إلى بريدك الإلكتروني.",
  code: "الرمز",
  verify: "دخول",
  wrongCode: "الرمز غير صحيح أو منتهي الصلاحية.",
  tooMany: "طلبت رموزًا كثيرة. حاول مرة أخرى بعد ساعة.",
  or: "أو",
  verifying: "جارٍ تسجيل دخولك…",
  logout: "تسجيل الخروج",
  myOrders: "طلباتي",
  newOrder: "ابدأ طلبًا جديدًا",
  noOrders: "لا توجد طلبات بعد. أخبرنا ماذا تريد أن تصنع.",
  thinking: "أوريون يفكر…",
  send: "إرسال",
  typeMessage: "اكتب إجابتك…",
  submit: "متابعة",
  optional: "اختياري",
  summary: "ملخص منتجك",
  confirm: "أكّد وأرسل إلى المصانع",
  requestChanges: "أريد تعديل شيء",
  changesPlaceholder: "ما الذي تريد تعديله؟",
  sendChanges: "أرسل التعديلات",
  waitingTitle: "نعمل على طلبك",
  waitingText: "نتواصل مع المصانع بخصوص منتجك، وسنبلغك فور وجود أي جديد.",
  size: "المقاس",
  qty: "عدد القطع",
  addSize: "أضف مقاسًا",
  total: "الإجمالي",
  loading: "جارٍ التحميل…",
  error: "حدث خطأ. حاول مرة أخرى.",
  back: "رجوع",
  switchLang: "English",
  orderTitle: "الطلب",
  status: "الحالة",
  updated: "آخر تحديث",
  pieces: "قطعة",
};

const dictionaries = { en, ar };
export type TextKey = keyof typeof en;

type LangContextValue = { lang: Lang; setLang: (l: Lang) => void; t: (key: TextKey) => string };
const LangContext = createContext<LangContextValue | null>(null);

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("ar");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("orion-lang");
      if (saved === "en" || saved === "ar") setLangState(saved);
    } catch {
      /* storage blocked: keep Arabic */
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem("orion-lang", l);
    } catch {
      /* ignore */
    }
  }, []);

  const t = useCallback((key: TextKey) => dictionaries[lang][key], [lang]);
  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>;
}

export function useLang(): LangContextValue {
  const value = useContext(LangContext);
  if (!value) throw new Error("useLang outside LangProvider");
  return value;
}
