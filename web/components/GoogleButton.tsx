"use client";

// "Sign in with Google" via Google Identity Services. Google gives us a signed ID token,
// which the API verifies against our client id. Hidden when no client id is configured.
import { useEffect, useRef } from "react";

import { googleLogin, type User } from "@/lib/api";
import { useLang } from "@/lib/i18n";

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

type GoogleId = {
  initialize: (o: { client_id: string; callback: (r: { credential: string }) => void }) => void;
  renderButton: (el: HTMLElement, o: Record<string, unknown>) => void;
};
declare global {
  interface Window { google?: { accounts: { id: GoogleId } } }
}

function loadScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts) return resolve();
    const existing = document.getElementById("gsi-client");
    if (existing) {
      existing.addEventListener("load", () => resolve());
      return;
    }
    const s = document.createElement("script");
    s.id = "gsi-client";
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Google script failed to load"));
    document.head.appendChild(s);
  });
}

export default function GoogleButton({ onSignedIn, onError }: { onSignedIn: (u: User) => void; onError: (m: string) => void }) {
  const { lang } = useLang();
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!CLIENT_ID) return;
    let cancelled = false;
    loadScript()
      .then(() => {
        if (cancelled || !box.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: async ({ credential }) => {
            try {
              onSignedIn(await googleLogin(credential));
            } catch {
              onError("Google sign-in failed");
            }
          },
        });
        box.current.replaceChildren();
        window.google.accounts.id.renderButton(box.current, {
          theme: "outline", size: "large", shape: "pill", width: 320, locale: lang, text: "continue_with",
        });
      })
      .catch((e: Error) => onError(e.message));
    return () => {
      cancelled = true;
    };
  }, [lang, onSignedIn, onError]);

  if (!CLIENT_ID) return null;
  return <div ref={box} style={{ display: "flex", justifyContent: "center" }} />;
}
