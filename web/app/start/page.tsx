"use client";

// /start (docs/website/02-start.md): sign in or sign up, then a short onboarding the first time: business,
// delivery address, preferences. Everything can be finished later. The AI reads the business details at the
// start of every order. TODO(decide): customs fields (none are asked until the team confirms they are needed).
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AddressForm, BusinessDetailsForm } from "@/components/BusinessForms";
import { CheckIcon } from "@/components/Icons";
import { api, type BusinessView } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { COMMON, t, type T } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";
import LoginPage from "../login/page";

const C = {
  step: t("الخطوة {n} من 3", "Step {n} of 3"),
  businessTitle: t("عرّفنا بنشاطك", "Tell us about your business"),
  businessText: t("يساعد المساعد على اقتراح ما يناسبك في كل طلب.", "It helps the assistant suggest what fits you in every order."),
  addressTitle: t("إلى أين نشحن؟", "Where do we ship to?"),
  addressText: t("عنوان مستودعك أو مكان التسليم، ومن يستلم الشحنة.", "Your warehouse or delivery place, and who receives the shipment."),
  prefsTitle: t("تفضيلاتك", "Your preferences"),
  prefsText: t("يمكنك تغييرها في أي وقت من الإعدادات.", "You can change these any time in Settings."),
  emailUpdates: t("أرسل لي التحديثات المهمة بالبريد الإلكتروني", "Email me important updates"),
  doneTitle: t("كل شيء جاهز", "You're all set"),
  doneText: t("صف منتجك الأول، ونتولى الباقي.", "Describe your first product, and we handle the rest."),
  start: t("ابدأ طلبك الأول", "Start your first order"),
  dashboard: t("اذهب إلى لوحتي", "Go to my dashboard"),
  continue: t("متابعة", "Continue"),
  skip: t("أكمل لاحقًا", "Finish later"),
};

export default function StartPage() {
  const { user, ready } = useAuth();
  const { me } = useMe();
  const router = useRouter();
  useEffect(() => {
    if (user && me?.onboarded) router.replace("/dashboard");
  }, [user, me, router]);

  if (!ready) return null;
  if (!user) return <LoginPage />;
  if (!me || me.onboarded) return null;
  return <Onboarding />;
}

function Onboarding() {
  const { lang, setLang } = useLang();
  const { me, update, refresh } = useMe();
  const router = useRouter();
  const L = (x: T) => x[lang];
  const [step, setStep] = useState(1);
  const [business, setBusiness] = useState<BusinessView | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => { api<BusinessView>("/business").then(setBusiness).catch(() => setError(true)); }, []);

  async function finish(to: string) {
    await api("/me/onboarded", { method: "POST" }).catch(() => {});
    router.replace(to);
    refresh().catch(() => {});
  }

  if (!business || !me) return <p className={error ? "error" : "muted"}>{error ? L(COMMON.error) : L(COMMON.loading)}</p>;
  const emailOn = Object.values(me.notify).every((n) => n.email);

  return (
    <div className="onboard board board-glass">
      <div className="spread">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/brand/mark-gold.png" alt="" width={40} height={38} />
        {step <= 3 && <button type="button" className="link-btn" onClick={() => finish("/dashboard")}>{L(C.skip)}</button>}
      </div>
      {step <= 3 && (
        <>
          <div className="onboard-steps" aria-label={L(C.step).replace("{n}", String(step))}>
            {[1, 2, 3].map((n) => <span key={n} className={n <= step ? "on" : ""} />)}
          </div>
          <span className="muted small">{L(C.step).replace("{n}", String(step))}</span>
        </>
      )}

      {step === 1 && (
        <>
          <div><h1 style={{ margin: 0 }}>{L(C.businessTitle)}</h1><p className="muted">{L(C.businessText)}</p></div>
          <BusinessDetailsForm profile={business.profile} submitLabel={L(C.continue)} onSaved={(v) => { setBusiness(v); setStep(2); }} />
        </>
      )}

      {step === 2 && (
        <>
          <div><h1 style={{ margin: 0 }}>{L(C.addressTitle)}</h1><p className="muted">{L(C.addressText)}</p></div>
          <AddressForm address={business.addresses.find((a) => a.is_default) ?? null} submitLabel={L(C.continue)}
            onSaved={(v) => { setBusiness(v); setStep(3); }} />
          <button type="button" className="link-btn" style={{ alignSelf: "flex-start" }} onClick={() => setStep(3)}>{L(COMMON.later)}</button>
        </>
      )}

      {step === 3 && (
        <>
          <div><h1 style={{ margin: 0 }}>{L(C.prefsTitle)}</h1><p className="muted">{L(C.prefsText)}</p></div>
          <div className="segmented" role="radiogroup">
            {(["ar", "en"] as const).map((l) => (
              <button key={l} type="button" role="radio" aria-checked={lang === l} className={lang === l ? "on" : ""}
                onClick={() => { setLang(l); update({ lang: l }).catch(() => {}); }}>{l === "ar" ? "العربية" : "English"}</button>
            ))}
          </div>
          <label className="check-row">
            <input type="checkbox" checked={emailOn} onChange={(e) => update({
              notify: Object.fromEntries(Object.entries(me.notify).map(([k, v]) => [k, { ...v, email: e.target.checked }])) as typeof me.notify,
            }).catch(() => {})} />
            {L(C.emailUpdates)}
          </label>
          <button type="button" className="btn" style={{ alignSelf: "flex-start" }} onClick={() => setStep(4)}>{L(C.continue)}</button>
        </>
      )}

      {step === 4 && (
        <div className="stack" style={{ alignItems: "flex-start" }}>
          <span className="empty-icon"><CheckIcon /></span>
          <h1 style={{ margin: 0 }}>{L(C.doneTitle)}</h1>
          <p className="muted" style={{ margin: 0 }}>{L(C.doneText)}</p>
          <div className="row">
            <button type="button" className="btn" onClick={() => finish("/orders/new")}>{L(C.start)}</button>
            <button type="button" className="btn-ghost" onClick={() => finish("/dashboard")}>{L(C.dashboard)}</button>
          </div>
        </div>
      )}
    </div>
  );
}
