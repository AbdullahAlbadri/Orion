"use client";

// The signed-in customer's settings (/me) and unread updates, shared by the shell and every page.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { api, type Me } from "./api";
import { useAuth } from "./auth";
import type { Calendar } from "./copy";

type MeValue = {
  me: Me | null;
  calendar: Calendar;
  unread: number;
  refresh: () => Promise<void>;
  refreshUnread: () => Promise<void>;
  update: (fields: Partial<Me>) => Promise<Me>;
};

const MeContext = createContext<MeValue | null>(null);

/** The first word of the customer's name, for greetings ("Hello Abdullah"). Empty when no name is saved. */
export function firstName(name: string | null | undefined): string {
  return name?.trim().split(/\s+/)[0] ?? "";
}

export function MeProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [me, setMe] = useState<Me | null>(null);
  const [unread, setUnread] = useState(0);

  const refresh = useCallback(async () => { setMe(await api<Me>("/me")); }, []);
  const refreshUnread = useCallback(async () => {
    const r = await api<{ unread: number }>("/notifications");
    setUnread(r.unread);
  }, []);
  const update = useCallback(async (fields: Partial<Me>) => {
    const next = await api<Me>("/me", { method: "PUT", body: fields });
    setMe(next);
    return next;
  }, []);

  useEffect(() => {
    if (!user) { setMe(null); setUnread(0); return; }
    refresh().catch(() => {});
    refreshUnread().catch(() => {});
    // Updates arrive without a refresh: check now and then while the tab is visible
    const timer = setInterval(() => { if (!document.hidden) refreshUnread().catch(() => {}); }, 60_000);
    return () => clearInterval(timer);
  }, [user, refresh, refreshUnread]);

  return (
    <MeContext.Provider value={{ me, calendar: me?.calendar ?? "gregorian", unread, refresh, refreshUnread, update }}>
      {children}
    </MeContext.Provider>
  );
}

export function useMe(): MeValue {
  const value = useContext(MeContext);
  if (!value) throw new Error("useMe outside MeProvider");
  return value;
}
