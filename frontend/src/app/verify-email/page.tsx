"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { confirmEmailVerification } from "@/features/auth/services/authClient";
import { useSafeAuth } from "@/features/auth/hooks/useSafeAuth";

function VerifyEmailInner() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const auth = useSafeAuth();
  const t = useTranslations("auth");

  const [state, setState] = useState<"verifying" | "verified" | "invalid">(
    token ? "verifying" : "invalid",
  );

  useEffect(() => {
    if (!token) {
      setState("invalid");
      return;
    }

    let active = true;
    confirmEmailVerification(token)
      .then(async () => {
        try {
          await auth?.refresh();
        } catch {
          // ignore post-verification refresh error
        }
        if (active) setState("verified");
      })
      .catch(() => {
        if (active) setState("invalid");
      });

    return () => {
      active = false;
    };
  }, [token, auth]);

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center bg-[#0A0E17] px-4 py-12 text-slate-100">
      <div className="surface-panel w-full max-w-md rounded-2xl border border-white/10 bg-[#0F1522] p-8 text-center space-y-4 text-slate-100">
        <h1 className="text-xl font-bold text-white">
          {t("verifyEmailTitle")}
        </h1>
        {state === "verifying" && (
          <p className="text-sm text-slate-400">{t("verifyConfirming")}</p>
        )}
        {state === "verified" && (
          <>
            <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-sm font-medium text-emerald-300">
              {t("verifySuccess")}
            </p>
            <Link
              href="/account"
              className="btn-primary inline-flex w-full justify-center py-3 text-sm font-semibold"
            >
              {t("accountSettings")}
            </Link>
          </>
        )}
        {state === "invalid" && (
          <>
            <p
              role="alert"
              className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-sm font-medium text-rose-200"
            >
              {t("verifyInvalidToken")}
            </p>
            <Link
              href="/account"
              className="btn-secondary inline-flex w-full justify-center py-3 text-sm font-medium"
            >
              {t("accountSettings")}
            </Link>
          </>
        )}
      </div>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailInner />
    </Suspense>
  );
}
