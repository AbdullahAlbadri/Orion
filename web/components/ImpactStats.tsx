"use client";

// "What Orion did for you": real counts from the customer's orders, plus a clearly labelled time estimate.
import { useEffect, useState } from "react";

import { api, type CustomerStats } from "@/lib/api";
import { useLang } from "@/lib/i18n";
import { BoxIcon, ChatIcon, ClockIcon, FactoryIcon, HashIcon, LightbulbIcon, SparkleIcon } from "./Icons";
import TopoTexture from "./TopoTexture";

export default function ImpactStats() {
  const { t } = useLang();
  const [s, setS] = useState<CustomerStats | null>(null);
  const [showBasis, setShowBasis] = useState(false);

  useEffect(() => {
    api<CustomerStats>("/orders/stats").then(setS).catch(() => setS(null));
  }, []);
  if (!s) return null;

  // Western digits for figures: the Arabic-Indic zero looks like a dot
  const num = (n: number) => n.toLocaleString("en-GB");
  const duration = (hours: number) =>
    hours >= 48 ? `${num(Math.round(hours / 24))} ${t("unitDays")}` : `${num(Math.round(hours * 10) / 10)} ${t("unitHours")}`;

  return (
    <>
      <div className="section-title"><h2>{t("impactTitle")}</h2></div>
      <div className="impact-grid">
        <div className="board board-ink cross impact-hero">
          <TopoTexture />
          <span className="icon"><ClockIcon /></span>
          <span className="muted">{t("timeSaved")}</span>
          <span className="impact-big">{s.time_saved_hours > 0 ? `≈ ${duration(s.time_saved_hours)}` : "—"}</span>
          {s.time_saved_hours === 0 && <span className="muted small">{t("statsStartAfter")}</span>}
          <button type="button" className="hint-chip" onClick={() => setShowBasis(!showBasis)}>
            <LightbulbIcon /> {t("howEstimated")}
          </button>
          {showBasis && (
            <p className="muted small" style={{ margin: 0 }}>
              {t("timeBasis")
                .replace("{spec}", num(s.time_saved_basis.per_spec))
                .replace("{factory}", num(s.time_saved_basis.per_factory))
                .replace("{message}", num(s.time_saved_basis.per_message * 60))}
            </p>
          )}
        </div>

        <div className="board board-paper cross impact-hero">
          <span className="icon"><SparkleIcon /></span>
          <span className="muted">{t("moneySaved")}</span>
          <span className="impact-big">{s.money_saved == null ? "—" : num(s.money_saved)}</span>
          <span className="muted small">{t("moneySavedLater")}</span>
        </div>

        <Small icon={<FactoryIcon />} label={t("factoriesContacted")} value={num(s.factories_contacted)} />
        <Small icon={<ChatIcon />} label={t("messagesHandled")} value={num(s.messages_handled)} />
        <Small icon={<HashIcon />} label={t("piecesOrdered")} value={num(s.pieces_ordered)} />
        <Small icon={<BoxIcon />} label={t("timeToQuote")}
          value={s.hours_to_first_quote == null ? "—" : duration(s.hours_to_first_quote)} />
      </div>
    </>
  );
}

function Small({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="board board-glass impact-small">
      <span className="icon">{icon}</span>
      <span className="muted small">{label}</span>
      <strong className="impact-value">{value}</strong>
    </div>
  );
}
