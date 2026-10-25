"use client";

// Settings (docs/website/app/22-settings.md): account, display, notifications, privacy, security, legal.
// TODO(decide): account deletion policy (orders in progress); email change with re-confirmation; two-factor later.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DownloadIcon, LogoutIcon } from "@/components/Icons";
import LegalDrawer from "@/components/LegalDrawer";
import { PageHead } from "@/components/ui";
import { api, downloadFile, type Me, type NotifyEvent } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useRequireUser } from "@/lib/auth";
import { COMMON, formatDate, NAV, num, t, type T } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";

const C = {
  profile: t("الملف الشخصي", "Profile"),
  name: t("الاسم", "Name"), phone: t("الجوال", "Mobile"), email: t("البريد الإلكتروني", "Email"),
  signIn: t("طريقة الدخول", "Sign-in method"),
  signInValue: t("رمز يصلك على بريدك، أو حساب Google", "A code sent to your email, or your Google account"),
  emailChange: t("لتغيير بريدك الإلكتروني، اطلب ذلك من فريقنا وسنؤكده معك.", "To change your email, ask our team and we'll confirm it with you."),
  badPhone: t("أدخل رقمًا صحيحًا، مثل ‎+966 5x xxx xxxx", "Enter a valid number, like +966 5x xxx xxxx"),
  display: t("اللغة والعرض", "Language and display"),
  language: t("اللغة", "Language"),
  calendar: t("التقويم", "Calendar"), gregorian: t("ميلادي", "Gregorian"), hijri: t("هجري", "Hijri"), both: t("كلاهما", "Both"),
  currency: t("عرض العملة", "Currency display"),
  currencyNote: t("يُستخدم عند عرض الأسعار في عروض الأسعار والمدفوعات.", "Used when prices are shown in quotes and payments."),
  displayNote: t("ينطبق على كل الصفحات، بما فيها طلباتك الحالية.", "Applies to every page, including your existing orders."),
  notifications: t("الإشعارات", "Notifications"),
  notifyNote: t("ينطبق على التحديثات القادمة لكل طلباتك، بما فيها الجارية.", "Applies to future updates on all your orders, including those in progress."),
  event: t("الحدث", "Event"), byEmail: t("البريد", "Email"), inApp: t("داخل الموقع", "In the app"),
  privacy: t("الخصوصية والبيانات", "Privacy and data"),
  download: t("تنزيل بياناتي", "Download my data"),
  downloadNote: t("ملف واحد بكل ما نحفظه عنك: الحساب، النشاط، العناوين، الطلبات وتفاصيلها، الملفات وطلبات المساعدة.",
    "One file with everything we keep about you: account, business, addresses, orders and their details, files and help requests."),
  remove: t("حذف الحساب", "Delete my account"),
  removeNote: t("لحذف حسابك، أرسل طلبًا لفريقنا. نراجع أولًا الطلبات الجارية قبل الحذف.",
    "To delete your account, send our team a request. We first check any orders in progress."),
  removeLink: t("طلب حذف الحساب", "Request account deletion"),
  security: t("الأمان", "Security"),
  sessions: t("الأجهزة المسجّل دخولها: {n}", "Signed-in devices: {n}"),
  since: t("منذ", "since"),
  signOutAll: t("تسجيل الخروج من كل الأجهزة", "Sign out everywhere"),
  signOutAllSure: t("سيُطلب منك تسجيل الدخول من جديد على كل الأجهزة، بما فيها هذا.", "You'll have to sign in again on every device, this one included."),
  confirm: t("تأكيد", "Confirm"),
  twoFactor: t("التحقق بخطوتين: لاحقًا.", "Two-step verification: coming later."),
  legal: t("الشروط والخصوصية", "Terms and privacy"),
  legalOpen: t("عرض الشروط والخصوصية والاسترجاع والمنتجات الممنوعة والملكية الفكرية", "Terms, privacy, refunds, restricted products and IP"),
};
const EVENTS: Record<NotifyEvent, T> = {
  quote_ready: t("عرض السعر جاهز", "Quote ready"), payment_received: t("استلام الدفعة", "Payment received"),
  sample_update: t("تحديث العينة", "Sample update"), shipped: t("الشحن", "Shipped"), delivered: t("التسليم", "Delivered"),
  delay: t("تأخير", "Delay"), problem: t("مشكلة", "Problem"),
};

export default function SettingsPage() {
  const user = useRequireUser();
  const { lang, setLang } = useLang();
  const { me, update, calendar } = useMe();
  const { signOut } = useAuth();
  const router = useRouter();
  const L = (x: T) => x[lang];
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<{ created_at: string }[] | null>(null);
  const [confirmAll, setConfirmAll] = useState(false);
  const [legal, setLegal] = useState(false);

  useEffect(() => { if (me) { setName(me.name ?? ""); setPhone(me.phone ?? ""); } }, [me]);
  useEffect(() => { if (user) api<{ created_at: string }[]>("/me/sessions").then(setSessions).catch(() => setSessions([])); }, [user]);

  if (!user || !me) return <p className="muted">{L(COMMON.loading)}</p>;

  async function save(section: string, fields: Partial<Me>) {
    setError(null);
    try {
      await update(fields);
      setSaved(section);
      setTimeout(() => setSaved((s) => (s === section ? null : s)), 2000);
    } catch { setError(L(COMMON.error)); }
  }
  const badPhone = phone.trim() !== "" && !/^\+?[0-9][0-9 \-]{6,18}$/.test(phone.trim());
  const Saved = ({ id }: { id: string }) => (saved === id ? <span className="saved-note">{L(COMMON.saved)}</span> : null);

  return (
    <>
      <PageHead title={L(NAV.settings)} />
      {error && <p className="error">{error}</p>}

      <section className="board board-glass">
        <h2>{L(C.profile)}</h2>
        <form className="form-grid" onSubmit={(e) => { e.preventDefault(); if (!badPhone) save("profile", { name: name.trim() || null, phone: phone.trim() || null }); }}>
          <div className="field"><label htmlFor="s-name">{L(C.name)}</label><input id="s-name" value={name} maxLength={100} onChange={(e) => setName(e.target.value)} /></div>
          <div className="field"><label htmlFor="s-phone">{L(C.phone)}</label>
            <input id="s-phone" dir="ltr" value={phone} onChange={(e) => setPhone(e.target.value)} aria-invalid={badPhone} />
            {badPhone && <div className="field-error">{L(C.badPhone)}</div>}</div>
          <div className="field"><label>{L(C.email)}</label><input value={me.email} dir="ltr" readOnly disabled />
            <div className="hint">{L(C.emailChange)} <Link href="/help?topic=account">{L(NAV.help)}</Link></div></div>
          <div className="field"><label>{L(C.signIn)}</label><p className="muted" style={{ margin: "10px 0 0" }}>{L(C.signInValue)}</p></div>
          <div className="form-actions full"><button className="btn btn-sm" disabled={badPhone}>{L(COMMON.save)}</button><Saved id="profile" /></div>
        </form>
      </section>

      <section className="board board-glass section-gap">
        <h2>{L(C.display)}</h2>
        <div className="form-grid">
          <div className="field"><label htmlFor="s-lang">{L(C.language)}</label>
            <select id="s-lang" value={lang} onChange={(e) => { const v = e.target.value as "ar" | "en"; setLang(v); save("display", { lang: v }); }}>
              <option value="ar">العربية</option><option value="en">English</option>
            </select></div>
          <div className="field"><label htmlFor="s-cal">{L(C.calendar)}</label>
            <select id="s-cal" value={calendar} onChange={(e) => save("display", { calendar: e.target.value as Me["calendar"] })}>
              <option value="gregorian">{L(C.gregorian)}</option><option value="hijri">{L(C.hijri)}</option><option value="both">{L(C.both)}</option>
            </select>
            <div className="hint">{formatDate(new Date().toISOString(), lang, calendar)}</div></div>
          <div className="field"><label htmlFor="s-cur">{L(C.currency)}</label>
            <select id="s-cur" value={me.currency} onChange={(e) => save("display", { currency: e.target.value as Me["currency"] })}>
              <option value="SAR">SAR · ﷼</option><option value="USD">USD · $</option>
            </select>
            <div className="hint">{L(C.currencyNote)}</div></div>
        </div>
        <p className="muted small" style={{ marginTop: 12 }}>{L(C.displayNote)} <Saved id="display" /></p>
      </section>

      <section className="board board-glass section-gap">
        <h2>{L(C.notifications)}</h2>
        <table className="table notify-table">
          <thead><tr><th>{L(C.event)}</th><th>{L(C.byEmail)}</th><th>{L(C.inApp)}</th></tr></thead>
          <tbody>
            {(Object.keys(EVENTS) as NotifyEvent[]).map((ev) => (
              <tr key={ev}>
                <td>{L(EVENTS[ev])}</td>
                {(["email", "in_app"] as const).map((ch) => (
                  <td key={ch} data-label={L(ch === "email" ? C.byEmail : C.inApp)}>
                    <input type="checkbox" className="toggle" checked={me.notify[ev][ch]} aria-label={`${L(EVENTS[ev])} · ${L(ch === "email" ? C.byEmail : C.inApp)}`}
                      onChange={(e) => save("notify", { notify: { ...me.notify, [ev]: { ...me.notify[ev], [ch]: e.target.checked } } })} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted small" style={{ margin: 0 }}>{L(C.notifyNote)} <Saved id="notify" /></p>
      </section>

      <section className="board board-glass section-gap stack">
        <h2 style={{ margin: 0 }}>{L(C.privacy)}</h2>
        <div className="spread">
          <p className="muted" style={{ margin: 0, maxWidth: 620 }}>{L(C.downloadNote)}</p>
          <button type="button" className="btn-ghost" onClick={() => downloadFile("/me/export", "orion-my-data.json").catch(() => setError(L(COMMON.error)))}>
            <DownloadIcon width={18} height={18} /> {L(C.download)}</button>
        </div>
        <div className="spread">
          <div><strong>{L(C.remove)}</strong><p className="muted" style={{ margin: 0 }}>{L(C.removeNote)}</p></div>
          <Link href="/help?topic=account" className="btn-outline">{L(C.removeLink)}</Link>
        </div>
      </section>

      <section className="board board-glass section-gap stack">
        <h2 style={{ margin: 0 }}>{L(C.security)}</h2>
        <div className="spread">
          <div>
            <strong>{L(C.sessions).replace("{n}", num(sessions?.length ?? 0))}</strong>
            {sessions && sessions.length > 0 && (
              <p className="muted small" style={{ margin: 0 }}>
                {sessions.map((s) => `${L(C.since)} ${formatDate(s.created_at, lang, calendar, true)}`).join(" · ")}
              </p>
            )}
          </div>
          {confirmAll ? (
            <div className="row">
              <span className="muted small" style={{ maxWidth: 280 }}>{L(C.signOutAllSure)}</span>
              <button type="button" className="btn btn-sm" onClick={async () => {
                await api("/me/sessions/revoke", { method: "POST" }).catch(() => {});
                await signOut();
                router.replace("/start");
              }}>{L(C.confirm)}</button>
              <button type="button" className="btn-ghost btn-sm" onClick={() => setConfirmAll(false)}>{L(COMMON.cancel)}</button>
            </div>
          ) : (
            <button type="button" className="btn-ghost" onClick={() => setConfirmAll(true)}><LogoutIcon width={18} height={18} /> {L(C.signOutAll)}</button>
          )}
        </div>
        <p className="muted small" style={{ margin: 0 }}>{L(C.twoFactor)}</p>
      </section>

      <section className="board board-glass section-gap spread">
        <h2 style={{ margin: 0 }}>{L(C.legal)}</h2>
        <button type="button" className="btn-outline" onClick={() => setLegal(true)}>{L(C.legalOpen)}</button>
      </section>
      <LegalDrawer open={legal} onClose={() => setLegal(false)} />
    </>
  );
}
