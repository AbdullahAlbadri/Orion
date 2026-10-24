"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { api, type OrderView } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { useLang } from "@/lib/i18n";

export default function NewOrderPage() {
  const user = useRequireUser();
  const { t } = useLang();
  const router = useRouter();
  const started = useRef(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!user || started.current) return;
    started.current = true;   // one order per visit, even with React's double effects in dev
    api<OrderView>("/orders", { method: "POST" })
      .then((order) => router.replace(`/orders/${order.order_id}`))
      .catch(() => setError(true));
  }, [user, router]);

  return <p className={error ? "error" : "muted"}>{error ? t("error") : t("loading")}</p>;
}
