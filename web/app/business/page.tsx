"use client";

// Business profile (docs/website/app/20-business-profile.md): what later stages need, and what is still missing.
// Addresses are changed only here, by the customer; the AI never changes them. Customs fields are not listed:
// TODO(decide) whether shipments need any customer customs details at all (see docs/website/landing-redesign.md §1).
import { useEffect, useState } from "react";

import BrandKit from "@/components/BrandKit";
import { AddressForm, BusinessDetailsForm } from "@/components/BusinessForms";
import { CheckIcon, PinIcon, PlusIcon, UsersIcon } from "@/components/Icons";
import { PageHead } from "@/components/ui";
import { api, type Address, type BusinessView, type Contact } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { COMMON, NAV, num, t, type T } from "@/lib/copy";
import { useLang } from "@/lib/i18n";

const C = {
  sub: t("ما نحتاجه لطلباتك وشحناتك، في مكان واحد.", "What your orders and shipments need, in one place."),
  progress: t("{done} من {total} مكتملة", "{done} of {total} complete"),
  firstOrder: t("قبل أول طلب", "Before your first order"),
  firstShipment: t("قبل أول شحنة", "Before your first shipment"),
  fix: t("أكمل", "Fix"),
  details: t("بيانات النشاط", "Business details"),
  brand: t("هوية العلامة", "Brand identity"),
  brandHint: t("شعارك وألوانك محفوظة هنا، ونقترحها عليك في كل طلب جديد لتضيفها بضغطة. ولا تُضاف إلى أي طلب إلا إذا اخترتها.",
    "Your logo and colours live here. Every new order suggests them so you can add them in one tap; they're only added if you choose them."),
  addresses: t("عناوين التوصيل", "Delivery addresses"),
  add: t("إضافة عنوان", "Add address"),
  default: t("افتراضي", "Default"),
  setDefault: t("اجعله افتراضيًا", "Make default"),
  removeSure: t("حذف هذا العنوان؟", "Remove this address?"),
  liveNote: t("لديك طلبات جارية. تغيير العنوان هنا لا يغيّر عنوان طلب لدى المصنع؛ اطلب ذلك من فريقنا عبر صفحة المساعدة ليؤكده.",
    "You have orders in progress. Changing an address here doesn't change an order already with a factory; ask our team through Help to confirm that."),
  noAddress: t("لا عناوين بعد.", "No addresses yet."),
  contacts: t("الأشخاص المخوّلون", "Authorised contacts"),
  contactsHint: t("من يمكنه التوقيع أو استلام الشحنات نيابة عن نشاطك.", "Who can sign for or receive shipments for your business."),
  contactName: t("الاسم", "Name"), contactPhone: t("الجوال", "Mobile"), role: t("الدور", "Role"),
  sign: t("يوقّع", "Signs"), receive: t("يستلم", "Receives"), both: t("يوقّع ويستلم", "Signs and receives"),
  addContact: t("إضافة شخص", "Add person"),
  shippingInfo: t("بيانات الشحنات", "Shipment details"),
  shippingInfoNote: t("نؤكد حاليًا ما تحتاجه الشحنات من بيانات إضافية. لن نطلب منك شيئًا آخر قبل أن نعرف أنه مطلوب فعلًا.",
    "We're confirming which extra details shipments need. We won't ask you for anything more until we know it's actually required."),
};
const ITEMS: Record<string, { label: T; target: string }> = {
  business_name: { label: t("اسم النشاط", "Business name"), target: "details" },
  description: { label: t("ماذا تبيع", "What you sell"), target: "details" },
  shipping_address: { label: t("عنوان التوصيل", "Delivery address"), target: "addresses" },
  receiver: { label: t("اسم المستلم وجواله", "Receiver's name and mobile"), target: "addresses" },
};

export default function BusinessPage() {
  const user = useRequireUser();
  const { lang } = useLang();
  const L = (x: T) => x[lang];
  const [v, setV] = useState<BusinessView | null>(null);
  const [error, setError] = useState(false);
  const [editing, setEditing] = useState<Address | "new" | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);

  useEffect(() => { if (user) api<BusinessView>("/business").then(setV).catch(() => setError(true)); }, [user]);
  if (!user || !v) return <p className={error ? "error" : "muted"}>{error ? L(COMMON.error) : L(COMMON.loading)}</p>;

  const c = v.completeness;
  const pct = Math.round((c.done / c.total) * 100);
  const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  async function act(path: string, method: string) {
    try { setV(await api<BusinessView>(path, { method })); } catch { setError(true); }
  }

  return (
    <>
      <PageHead title={L(NAV.business)} sub={L(C.sub)} />

      <section className="board board-glass">
        <div className="spread"><strong>{L(C.progress).replace("{done}", num(c.done)).replace("{total}", num(c.total))}</strong>
          <span className="muted small">{num(pct)}%</span></div>
        <div className="progress" style={{ marginTop: 10 }}><span style={{ width: `${pct}%` }} /></div>
        {(["first_order", "first_shipment"] as const).map((group) => (
          <div key={group}>
            <div className="pane-group" style={{ marginTop: 14 }}>{L(group === "first_order" ? C.firstOrder : C.firstShipment)}</div>
            <ul className="checklist" style={{ marginTop: 4 }}>
              {c.items.filter((i) => i.group === group).map((i) => (
                <li key={i.id} className={i.done ? "done" : ""}>
                  <span className="tick">{i.done && <CheckIcon width={14} height={14} />}</span>
                  <span className="grow">{L(ITEMS[i.id].label)}</span>
                  {!i.done && <button type="button" className="btn-outline" onClick={() => jump(ITEMS[i.id].target)}>{L(C.fix)}</button>}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <section id="details" className="section-gap">
        <div className="section-title"><h2>{L(C.details)}</h2></div>
        <div className="board board-glass"><BusinessDetailsForm profile={v.profile} onSaved={setV} /></div>
      </section>

      <section id="brand" className="section-gap">
        <div className="section-title"><h2>{L(C.brand)}</h2></div>
        <p className="muted">{L(C.brandHint)}</p>
        <div className="board board-glass"><BrandKit view={v} onSaved={setV} /></div>
      </section>

      <section id="addresses" className="section-gap">
        <div className="section-title"><h2>{L(C.addresses)}</h2>
          {editing === null && v.addresses.length < 10 && (
            <button type="button" className="btn-ghost btn-sm" onClick={() => setEditing("new")}><PlusIcon width={16} height={16} /> {L(C.add)}</button>
          )}</div>
        {v.live_orders > 0 && <p className="note">{L(C.liveNote)}</p>}
        {editing !== null && (
          <div className="board board-glass" style={{ marginBottom: 14 }}>
            <AddressForm address={editing === "new" ? null : editing} onCancel={() => setEditing(null)}
              onSaved={(next) => { setV(next); setEditing(null); }} />
          </div>
        )}
        {v.addresses.length === 0 && editing === null ? <p className="muted">{L(C.noAddress)}</p> : (
          <div className="card-grid">
            {v.addresses.map((a) => (
              <div key={a.id} className="order-card">
                <div className="spread"><strong><PinIcon width={16} height={16} /> {a.label || a.city}</strong>
                  {a.is_default && <span className="st st-you">{L(C.default)}</span>}</div>
                <div className="muted small">
                  {a.contact_name} · <span dir="ltr">{a.phone}</span><br />
                  {[a.street, a.building, a.district, a.city, a.postal_code].filter(Boolean).join("، ")}
                  {a.notes && <><br />{a.notes}</>}
                </div>
                <div className="row">
                  <button type="button" className="btn-outline" onClick={() => setEditing(a)}>{L(COMMON.edit)}</button>
                  {!a.is_default && <button type="button" className="link-btn" onClick={() => act(`/business/addresses/${a.id}/default`, "POST")}>{L(C.setDefault)}</button>}
                  {removing === a.id ? (
                    <>
                      <span className="muted small">{L(C.removeSure)}</span>
                      <button type="button" className="btn btn-sm" onClick={() => { setRemoving(null); act(`/business/addresses/${a.id}`, "DELETE"); }}>{L(COMMON.remove)}</button>
                      <button type="button" className="btn-ghost btn-sm" onClick={() => setRemoving(null)}>{L(COMMON.cancel)}</button>
                    </>
                  ) : <button type="button" className="link-btn" onClick={() => setRemoving(a.id)}>{L(COMMON.remove)}</button>}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section-gap">
        <div className="section-title"><h2>{L(C.contacts)}</h2></div>
        <p className="muted">{L(C.contactsHint)}</p>
        <Contacts contacts={v.profile.contacts} onSaved={setV} />
      </section>

      <section className="section-gap">
        <div className="section-title"><h2>{L(C.shippingInfo)}</h2></div>
        <p className="note">{L(C.shippingInfoNote)}</p>
      </section>
    </>
  );
}

function Contacts({ contacts, onSaved }: { contacts: Contact[]; onSaved: (v: BusinessView) => void }) {
  const { lang } = useLang();
  const L = (x: T) => x[lang];
  const [list, setList] = useState<Contact[]>(contacts);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(false);
  const update = (i: number, patch: Partial<Contact>) => setList(list.map((c, j) => (j === i ? { ...c, ...patch } : c)));

  async function save() {
    setBusy(true); setError(false);
    try {
      const clean = list.filter((c) => c.name.trim()).map((c) => ({ ...c, name: c.name.trim(), phone: c.phone?.trim() || null }));
      onSaved(await api<BusinessView>("/business", { method: "PUT", body: { contacts: clean } }));
      setSaved(true); setTimeout(() => setSaved(false), 2000);
    } catch { setError(true); } finally { setBusy(false); }
  }

  return (
    <div className="board board-glass stack">
      {list.map((c, i) => (
        <div key={i} className="form-grid contact-row">
          <div className="field"><label>{L(C.contactName)}</label><input value={c.name} maxLength={100} onChange={(e) => update(i, { name: e.target.value })} /></div>
          <div className="field"><label>{L(C.contactPhone)}</label><input dir="ltr" value={c.phone ?? ""} onChange={(e) => update(i, { phone: e.target.value })} /></div>
          <div className="field"><label>{L(C.role)}</label>
            <select value={c.role} onChange={(e) => update(i, { role: e.target.value as Contact["role"] })}>
              <option value="both">{L(C.both)}</option><option value="sign">{L(C.sign)}</option><option value="receive">{L(C.receive)}</option>
            </select></div>
          <button type="button" className="link-btn" onClick={() => setList(list.filter((_, j) => j !== i))}>{L(COMMON.remove)}</button>
        </div>
      ))}
      <div className="form-actions" style={{ marginTop: 0 }}>
        {list.length < 10 && <button type="button" className="btn-ghost btn-sm" onClick={() => setList([...list, { name: "", phone: "", role: "both" }])}>
          <UsersIcon width={16} height={16} /> {L(C.addContact)}</button>}
        <button type="button" className="btn btn-sm" onClick={save} disabled={busy}>{L(COMMON.save)}</button>
        {saved && <span className="saved-note">{L(COMMON.saved)}</span>}
        {error && <span className="error">{L(COMMON.error)}</span>}
      </div>
    </div>
  );
}
