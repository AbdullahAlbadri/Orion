"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import GoogleButton from "@/components/GoogleButton";
import { ArrowIcon, GlobeIcon } from "@/components/Icons";
import Stars from "@/components/landing/Stars";
import LegalDrawer from "@/components/LegalDrawer";
import { ApiError, startEmailLogin, verifyEmailLogin, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useLang } from "@/lib/i18n";

export default function LoginPage() {
  const { t, lang, setLang } = useLang();
  const { signedIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"email" | "code">("email");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [legal, setLegal] = useState(false);

  // /start sends new customers to onboarding and everyone else to the dashboard
  const done = useCallback((user: User) => {
    signedIn(user);
    router.replace("/start");
  }, [signedIn, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (step === "email") {
        await startEmailLogin(email);
        setStep("code");
      } else {
        done(await verifyEmailLogin(email, code));
      }
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      setError(status === 429 ? t("tooMany") : status === 401 ? t("wrongCode") : t("error"));
    } finally {
      setBusy(false);
    }
  }

  function back() {
    setStep("email");
    setCode("");
    setError(null);
  }

  return (
    <div className="auth-page">
      <Stars />
      <div className="auth-top">
        {step === "code" ? (
          <button type="button" className="auth-back" onClick={back}>
            <ArrowIcon width={18} height={18} className="auth-back-arrow" /> {t("back")}
          </button>
        ) : (
          <Link href="/" className="auth-back">
            <ArrowIcon width={18} height={18} className="auth-back-arrow" /> {t("back")}
          </Link>
        )}
        <button type="button" className="auth-lang" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
          <GlobeIcon width={16} height={16} /> {t("switchLang")}
        </button>
      </div>

      <div className="auth">
        <section className="auth-brand">
          <svg className="auth-orbit" viewBox="0 0 400 400" aria-hidden>
            <circle cx="200" cy="200" r="70" />
            <circle cx="200" cy="200" r="120" />
            <circle cx="200" cy="200" r="170" />
            <circle className="auth-planet" cx="200" cy="30" r="5">
              <animateTransform attributeName="transform" type="rotate" from="0 200 200" to="360 200 200" dur="40s" repeatCount="indefinite" />
            </circle>
            <circle className="auth-planet dim" cx="320" cy="200" r="3.5">
              <animateTransform attributeName="transform" type="rotate" from="0 200 200" to="-360 200 200" dur="70s" repeatCount="indefinite" />
            </circle>
          </svg>
          <div className="auth-brand-text">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className="mark-big" src="/brand/mark-gold.png" alt="" />
            <h1>{t("appName")}</h1>
            <p>{t("tagline")}</p>
          </div>
        </section>

        <form className="auth-form" onSubmit={submit}>
          <p className="auth-step">{step === "email" ? "01 / 02" : "02 / 02"}</p>
          <h2>{t("loginTitle")}</h2>
          <div>
            <label htmlFor="email">{t("email")}</label>
            <input id="email" type="email" dir="ltr" autoComplete="email" required value={email}
              disabled={step === "code"} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" />
          </div>
          {step === "code" && (
            <div>
              <p className="muted small">{t("codeSent")}</p>
              <label htmlFor="code">{t("code")}</label>
              <input id="code" className="auth-code" inputMode="numeric" autoComplete="one-time-code" dir="ltr" maxLength={6}
                required value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} autoFocus />
            </div>
          )}
          {error && <p className="error">{error}</p>}
          <button className="btn auth-submit" disabled={busy}>{step === "email" ? t("sendCode") : t("verify")}</button>
          {step === "email" && (
            <>
              <div className="divider">{t("or")}</div>
              <GoogleButton onSignedIn={done} onError={setError} />
            </>
          )}
          <p className="muted small" style={{ margin: 0 }}>
            {lang === "ar" ? "بالمتابعة، أنت توافق على " : "By continuing, you agree to Orion's "}
            <button type="button" className="link-btn" style={{ padding: 0 }} onClick={() => setLegal(true)}>
              {lang === "ar" ? "الشروط والخصوصية" : "terms and privacy policy"}
            </button>
          </p>
        </form>
      </div>
      <LegalDrawer open={legal} onClose={() => setLegal(false)} />
    </div>
  );
}
