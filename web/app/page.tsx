"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/lib/auth";
import { useLang } from "@/lib/i18n";

export default function Home() {
  const { user, ready } = useAuth();
  const { t } = useLang();
  const router = useRouter();

  useEffect(() => {
    if (ready) router.replace(user ? "/orders" : "/login");
  }, [ready, user, router]);

  return <p className="muted">{t("loading")}</p>;
}
