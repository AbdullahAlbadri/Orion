"use client";

// Target of the link in the login email: /login/verify?email=...&code=...
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { verifyEmailLogin } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useLang } from "@/lib/i18n";

function Verify() {
  const params = useSearchParams();
  const router = useRouter();
  const { signedIn } = useAuth();
  const { t } = useLang();
  const [failed, setFailed] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;   // a code works once; don't submit twice in dev double-render
    started.current = true;
    const email = params.get("email");
    const code = params.get("code");
    if (!email || !code) return setFailed(true);
    verifyEmailLogin(email, code)
      .then((user) => {
        signedIn(user);
        router.replace("/orders");
      })
      .catch(() => setFailed(true));
  }, [params, router, signedIn]);

  return (
    <div className="card">
      {failed ? (
        <>
          <p className="error">{t("wrongCode")}</p>
          <a href="/login">{t("back")}</a>
        </>
      ) : (
        <p className="muted">{t("verifying")}</p>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense>
      <Verify />
    </Suspense>
  );
}
