"use client";

// "Imagine your product": an AI picture made from the form as it is now and the customer's logo. Only an
// illustration (the summary is what gets made); a few per order, since each one is a paid model call.
import { useEffect, useState } from "react";

import { ApiError, listMockups, makeMockup, mockupUrl, type MockupList } from "@/lib/api";
import { t, type T } from "@/lib/copy";
import { useLang } from "@/lib/i18n";
import { DownloadIcon, SparkleIcon } from "./Icons";

const C = {
  button: t("تخيّل منتجك بالذكاء الاصطناعي", "Imagine your product with AI"),
  hint: t("صورة تقريبية من اختياراتك وشعارك، لتتخيل شكل المنتج قبل الطلب.",
    "A picture from your choices and your logo, to see roughly how it will look."),
  busy: t("نرسم منتجك… قد يستغرق ذلك حتى دقيقة", "Drawing your product… this can take up to a minute"),
  caption: t("صورة تخيلية بالذكاء الاصطناعي. المنتج الفعلي يُصنع حسب ملخص طلبك.",
    "AI illustration. The real product is made exactly to your order summary."),
  noLogo: t("لم يظهر شعارك: ارفعه بصيغة PNG أو JPG ليظهر في الصورة (صيغ SVG وPDF وAI لا تُقرأ هنا).",
    "Your logo isn't in the picture: upload it as PNG or JPG to see it (SVG, PDF and AI can't be used here)."),
  left: t("متبقٍ {n} من الصور لهذا الطلب", "{n} pictures left for this order"),
  none: t("استخدمت كل الصور المتاحة لهذا الطلب.", "You've used all the pictures for this order."),
  tooMany: t("طلبت صورًا كثيرة. حاول بعد قليل.", "Too many pictures for now. Try again a bit later."),
  failed: t("تعذّر رسم الصورة. حاول مرة أخرى.", "The picture couldn't be made. Please try again."),
  download: t("تنزيل", "Download"),
};

function MockupImage({ orderId, id, alt }: { orderId: string; id: string; alt: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    mockupUrl(orderId, id).then((u) => alive && setUrl(u)).catch(() => {});
    return () => { alive = false; };
  }, [orderId, id]);
  // eslint-disable-next-line @next/next/no-img-element
  return url ? <img src={url} alt={alt} /> : <span className="mockup-placeholder" />;
}

export default function MockupPanel({ orderId, answers }: { orderId: string; answers: Record<string, unknown> }) {
  const { lang } = useLang();
  const L = (x: T) => x[lang];
  const [list, setList] = useState<MockupList | null>(null);
  const [shown, setShown] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logoMissing, setLogoMissing] = useState(false);

  useEffect(() => {
    listMockups(orderId).then((l) => { setList(l); setShown(l.mockups[0]?.mockup_id ?? null); }).catch(() => {});
  }, [orderId]);

  async function make() {
    setBusy(true); setError(null);
    try {
      const r = await makeMockup(orderId, answers, lang);
      setList({ mockups: r.mockups, remaining: r.remaining });
      setShown(r.mockup_id);
      setLogoMissing(!r.logo_used);
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0;
      setError(L(status === 429 ? C.tooMany : status === 409 ? C.none : C.failed));
    } finally { setBusy(false); }
  }

  async function download() {
    if (!shown) return;
    const a = document.createElement("a");
    a.href = await mockupUrl(orderId, shown);
    a.download = `orion-mockup-${shown.slice(0, 8)}.png`;
    a.click();
  }

  const remaining = list?.remaining ?? 0;
  return (
    <div className="mockup-panel">
      <div className="spread">
        <div className="stack-sm">
          <button type="button" className="btn btn-sm mockup-btn" disabled={busy || (list !== null && remaining === 0)} onClick={make}>
            <SparkleIcon width={16} height={16} /> {busy ? L(C.busy) : L(C.button)}
          </button>
          <span className="muted small">{L(C.hint)}</span>
        </div>
        {list && <span className="muted small">{remaining > 0 ? L(C.left).replace("{n}", String(remaining)) : L(C.none)}</span>}
      </div>
      {busy && <div className="mockup-frame mockup-loading" aria-busy="true"><SparkleIcon /></div>}
      {!busy && shown && (
        <figure className="mockup-frame">
          <MockupImage orderId={orderId} id={shown} alt={L(C.caption)} />
          <figcaption className="spread">
            <span className="small">{L(C.caption)}</span>
            <button type="button" className="link-btn" onClick={download}><DownloadIcon width={16} height={16} /> {L(C.download)}</button>
          </figcaption>
        </figure>
      )}
      {logoMissing && !busy && <p className="note" style={{ margin: 0 }}>{L(C.noLogo)}</p>}
      {error && <p className="error small">{error}</p>}
      {list && list.mockups.length > 1 && (
        <div className="mockup-thumbs">
          {list.mockups.map((m) => (
            <button key={m.mockup_id} type="button" className={m.mockup_id === shown ? "on" : ""} onClick={() => setShown(m.mockup_id)}>
              <MockupImage orderId={orderId} id={m.mockup_id} alt="" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
