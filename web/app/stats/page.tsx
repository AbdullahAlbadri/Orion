"use client";

// Stats (docs/website/app/16-stats.md): honest numbers with their method one click away.
// Spend, cost breakdown and landed cost need payments (TODO(decide): provider) and stay hidden until then.
// "Money saved" is never shown without a stated baseline; time saved is labelled as an estimate.
import Link from "next/link";
import { useEffect, useState } from "react";

import { ChartIcon } from "@/components/Icons";
import ImpactStats from "@/components/ImpactStats";
import { Empty, Explain, PageHead, Tabs } from "@/components/ui";
import { api, type FullStats, type Phase } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { COMMON, duration, formatDate, NAV, num, t, type T } from "@/lib/copy";
import { HOME } from "@/lib/home";
import { useLang } from "@/lib/i18n";
import { useMe } from "@/lib/me";
import { orderName } from "@/lib/orders";

type Range = FullStats["range"];

const C = {
  sub: t("أين يذهب وقتك وطلباتك، بأرقام يمكنك التحقق منها.", "Where your time and orders go, in numbers you can check."),
  month: t("هذا الشهر", "This month"), quarter: t("3 أشهر", "3 months"), year: t("سنة", "Year"), all: t("كل الوقت", "All time"),
  submitted: t("طلبات مؤكدة", "Confirmed orders"),
  submittedHow: t("الطلبات التي أكدت ملخصها في الفترة المختارة (المسودات لا تُحسب).",
    "Orders whose summary you confirmed in the selected period (drafts don't count)."),
  pieces: t("قطع مطلوبة", "Pieces ordered"),
  piecesHow: t("مجموع الكميات في ملخصات الطلبات المؤكدة.", "The sum of quantities in your confirmed summaries."),
  toDelivery: t("من التأكيد إلى التسليم", "Confirmation to delivery"),
  toDeliveryHow: t("متوسط الوقت من تأكيد الملخص حتى تسجيل التسليم، للطلبات المُسلّمة فقط.",
    "Average time from confirming the summary to delivery, for delivered orders only."),
  mismatches: t("فروقات اكتشفناها", "Differences caught"),
  mismatchesHow: t("ردود المصانع التي اختلفت عن ملخصك المؤكد (الخامة، الكمية، اللون…) وأوقفناها قبل التنفيذ ليراجعها فريقنا.",
    "Factory replies that differed from your confirmed summary (material, quantity, colour…) and that we stopped for our team to review before anything was made."),
  spend: t("الإنفاق", "Spend"),
  spendLater: t("يظهر الإنفاق وتفصيل التكاليف وتكلفة القطعة الواصلة بعد أول دفعة.",
    "Spend, the cost breakdown and the landed cost per piece appear after your first payment."),
  time: t("الوقت", "Time"),
  perPhase: t("متوسط الوقت في كل مرحلة", "Average time per stage"),
  perPhaseHow: t("من سجل تغيّر مراحل طلباتك. تُحسب المرحلة بعد انتهائها فقط، حتى لا تخفّض الطلبات الجارية المتوسط.",
    "From the record of each stage change in your orders. A stage counts once it is finished, so orders still in it don't pull the average down."),
  waiting: t("بانتظار مَن؟", "Waiting on whom?"),
  waitingHow: t("الوقت الكلي الذي قضته طلباتك المؤكدة بانتظار كل طرف، بما فيه المرحلة الحالية حتى الآن.",
    "Total time your confirmed orders spent waiting on each party, including the current stage up to now."),
  orders: t("الطلبات", "Orders"),
  byStatus: t("حسب الحالة", "By status"), byMarket: t("حسب المجال", "By market"),
  reorderRate: t("نسبة إعادة الطلب", "Reorder rate"),
  reorderHow: t("الطلبات المؤكدة التي بدأت من منتج سابق ÷ كل الطلبات المؤكدة.", "Confirmed orders started from an earlier product ÷ all confirmed orders."),
  revisions: t("تعديلات بعد التأكيد", "Changes after confirming"),
  revisionsHow: t("عدد النسخ الجديدة من الملخص بعد النسخة الأولى.", "New versions of a summary after the first one."),
  perOrder: t("كل طلب", "Per order"),
  product: t("المنتج", "Product"), date: t("التاريخ", "Date"), status: t("الحالة", "Status"), qty: t("الكمية", "Quantity"),
  versions: t("النسخ", "Versions"), delivery: t("حتى التسليم", "To delivery"),
  early: t("تظهر إحصاءاتك بعد أول طلب مؤكد", "Your stats appear after your first confirmed order"),
  earlyText: t("نعرض فقط الأرقام التي لدينا بيانات لها: عدد الطلبات والقطع أولًا، ثم أوقات المراحل، ثم الإنفاق بعد أول دفعة.",
    "We only show numbers we have data for: orders and pieces first, then time per stage, then spend after your first payment."),
  noPhases: t("تظهر بعد أن تنهي طلباتك مرحلة واحدة على الأقل.", "Appears once your orders finish at least one stage."),
};

const PHASE: Record<Phase, T> = {
  specification: t("وصف المنتج والملخص", "Describing and summary"),
  quote: t("المصانع وعرض السعر", "Factories and quote"),
  payment: t("الموافقة والدفع", "Approval and payment"),
  sample: t("العينة", "Sample"),
  production: t("التصنيع", "Production"),
  shipping: t("الشحن", "Shipping"),
  customs: t("أوراق الشحنة", "Shipment paperwork"),
};
const OWNER: Record<string, T> = {
  customer: t("أنت", "You"), factory: t("المصنع", "The factory"), orion: t("فريق أوريون", "The Orion team"), shipping: t("شركة الشحن", "The carrier"),
};

export default function StatsPage() {
  const user = useRequireUser();
  const { lang } = useLang();
  const { calendar } = useMe();
  const L = (x: Record<"ar" | "en", string>) => x[lang];
  const [range, setRange] = useState<Range>("all");
  const [s, setS] = useState<FullStats | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (user) api<FullStats>(`/orders/stats?range=${range}`).then(setS).catch(() => setError(true));
  }, [user, range]);

  const head = (
    <>
      <PageHead title={L(NAV.stats)} sub={L(C.sub)} />
      <div className="toolbar">
        <Tabs<Range> value={range} onChange={setRange} options={[
          { key: "month", label: L(C.month) }, { key: "quarter", label: L(C.quarter) },
          { key: "year", label: L(C.year) }, { key: "all", label: L(C.all) },
        ]} />
      </div>
    </>
  );
  if (!user || !s) return <>{head}<p className={error ? "error" : "muted"}>{error ? L(COMMON.error) : L(COMMON.loading)}</p></>;

  const o = s.orders;
  if (o.submitted === 0) {
    return <>{head}<Empty icon={<ChartIcon />} title={L(C.early)} text={L(C.earlyText)}
      action={<Link href="/orders/new" className="btn">{L(COMMON.startFirst)}</Link>} /></>;
  }

  const statusLabel = Object.fromEntries(s.order_list.map((r) => [r.stage, r.status[lang]]));
  const marketLabel = (id: string) => HOME.markets.items.find((m) => m.id === id)?.name[lang] ?? id;
  const waitingTotal = Object.values(s.time.waiting_hours).reduce((a, b) => a + (b ?? 0), 0);

  return (
    <>
      {head}
      <div className="tiles">
        <Tile label={L(C.submitted)} value={num(o.submitted)} how={L(C.submittedHow)} />
        <Tile label={L(C.pieces)} value={num(o.pieces)} how={L(C.piecesHow)} />
        {s.time.order_to_delivery_hours != null && (
          <Tile label={L(C.toDelivery)} value={duration(s.time.order_to_delivery_hours, lang)} how={L(C.toDeliveryHow)} />
        )}
        <Tile label={L(C.mismatches)} value={num(o.mismatches_caught)} how={L(C.mismatchesHow)} />
      </div>

      <section className="section-gap">
        <div className="section-title"><h2>{L(C.spend)}</h2></div>
        <p className="note">{L(C.spendLater)}</p>
      </section>

      <section className="section-gap">
        <div className="section-title"><h2>{L(C.time)}</h2></div>
        <div className="grid-2">
          <div className="board board-glass">
            <h3>{L(C.perPhase)}</h3>
            {s.time.phases.length === 0 ? <p className="muted small">{L(C.noPhases)}</p> : (
              <Bars rows={s.time.phases.map((p) => ({ label: L(PHASE[p.phase]), value: p.avg_hours, text: duration(p.avg_hours, lang) }))} />
            )}
            <Explain>{L(C.perPhaseHow)}</Explain>
          </div>
          <div className="board board-glass">
            <h3>{L(C.waiting)}</h3>
            {waitingTotal === 0 ? <p className="muted small">{L(C.noPhases)}</p> : (
              <Bars rows={Object.entries(s.time.waiting_hours).map(([k, v]) => ({
                label: L(OWNER[k] ?? t(k, k)), value: v ?? 0,
                text: `${duration(v ?? 0, lang)} · ${num(Math.round(((v ?? 0) / waitingTotal) * 100))}%`,
              }))} />
            )}
            <Explain>{L(C.waitingHow)}</Explain>
          </div>
        </div>
      </section>

      <section className="section-gap">
        <div className="section-title"><h2>{L(C.orders)}</h2></div>
        <div className="grid-2">
          <div className="board board-glass">
            <h3>{L(C.byStatus)}</h3>
            <Bars rows={Object.entries(o.by_stage).map(([k, v]) => ({ label: statusLabel[k] ?? k, value: v, text: num(v) }))} />
          </div>
          <div className="board board-glass">
            <h3>{L(C.byMarket)}</h3>
            <Bars rows={Object.entries(o.by_market).map(([k, v]) => ({ label: marketLabel(k), value: v, text: num(v) }))} />
          </div>
        </div>
        <div className="tiles section-gap">
          <Tile label={L(C.reorderRate)} value={o.reorder_rate == null ? "—" : `${num(Math.round(o.reorder_rate * 100))}%`} how={L(C.reorderHow)} />
          <Tile label={L(C.revisions)} value={num(o.revisions)} how={L(C.revisionsHow)} />
        </div>
      </section>

      <ImpactStats />

      <section className="section-gap">
        <div className="section-title"><h2>{L(C.perOrder)}</h2></div>
        <table className="table">
          <thead><tr><th>{L(C.product)}</th><th>{L(C.date)}</th><th>{L(C.status)}</th><th>{L(C.qty)}</th>
            <th>{L(C.versions)}</th><th>{L(C.mismatches)}</th><th>{L(C.delivery)}</th></tr></thead>
          <tbody>
            {s.order_list.map((r) => {
              const hours = s.time.per_order[r.id]?.to_delivery_hours;
              return (
                <tr key={r.id}>
                  <td><Link href={`/orders/${r.id}`}>{orderName(r, lang)}</Link></td>
                  <td data-label={L(C.date)}>{formatDate(r.created_at, lang, calendar)}</td>
                  <td data-label={L(C.status)}>{r.status[lang]}</td>
                  <td data-label={L(C.qty)}>{r.quantity ? num(r.quantity) : "—"}</td>
                  <td data-label={L(C.versions)}>{num(r.revisions + 1)}</td>
                  <td data-label={L(C.mismatches)}>{num(r.mismatches_caught)}</td>
                  <td data-label={L(C.delivery)}>{hours == null ? "—" : duration(hours, lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </>
  );
}

function Tile({ label, value, how }: { label: string; value: string; how: string }) {
  return (
    <div className="tile">
      <span className="label">{label}</span>
      <span className="value">{value}</span>
      <Explain>{how}</Explain>
    </div>
  );
}

/** One measure as horizontal bars, values written at the end (single hue; the label names each bar). */
function Bars({ rows }: { rows: { label: string; value: number; text: string }[] }) {
  const max = Math.max(...rows.map((r) => r.value), 0) || 1;
  return (
    <div className="hbars">
      {rows.map((r) => (
        <div key={r.label} className="hbar" title={`${r.label}: ${r.text}`}>
          <span className="ellipsis">{r.label}</span>
          <span className="track"><span className="fill" style={{ width: `${Math.max(2, (r.value / max) * 100)}%` }} /></span>
          <span className="small">{r.text}</span>
        </div>
      ))}
    </div>
  );
}
