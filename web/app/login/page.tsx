"use client";

import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import GoogleButton from "@/components/GoogleButton";
import { GlobeIcon } from "@/components/Icons";
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

  const done = useCallback((user: User) => {
    signedIn(user);
    router.replace("/dashboard");
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

  return (
    <div className="auth">
      <section className="auth-brand">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="mark-big" src="/brand/mark-gold.png" alt="" />
        <div>
          <h1>{t("appName")}</h1>
          <p style={{ maxWidth: 340, opacity: 0.9 }}>{t("tagline")}</p>
        </div>
      </section>

      <form className="auth-form" onSubmit={submit}>
        <div className="spread">
          <h2 style={{ margin: 0 }}>{t("loginTitle")}</h2>
          <button type="button" className="btn-ghost btn-sm" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
            <GlobeIcon width={16} height={16} /> {t("switchLang")}
          </button>
        </div>
        <div>
          <label htmlFor="email">{t("email")}</label>
          <input id="email" type="email" dir="ltr" autoComplete="email" required value={email}
            disabled={step === "code"} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" />
        </div>
        {step === "code" && (
          <div>
            <p className="muted small">{t("codeSent")}</p>
            <label htmlFor="code">{t("code")}</label>
            <input id="code" inputMode="numeric" autoComplete="one-time-code" dir="ltr" maxLength={6} required
              value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} autoFocus
              style={{ letterSpacing: "0.4em", fontSize: 20, textAlign: "center" }} />
          </div>
        )}
        {error && <p className="error">{error}</p>}
        <button className="btn" disabled={busy}>{step === "email" ? t("sendCode") : t("verify")}</button>
        <div className="divider">{t("or")}</div>
        <GoogleButton onSignedIn={done} onError={setError} />
      </form>
    </div>
  );
}
