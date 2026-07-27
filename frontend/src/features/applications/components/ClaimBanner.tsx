"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useAuth } from "@/features/auth/context/AuthProvider";
import { claimApplication } from "../services/applicationsClient";
import {
  getSessionToken,
  removeSessionToken,
} from "@/features/form-session/services/sessionCredentials";

interface Props {
  sessionId: string;
}

/**
 * Shown only while an anonymous ownership token for this session still
 * exists in sessionStorage — once claimed, the token is cleared and the
 * banner naturally disappears on next render.
 */
export default function ClaimBanner({ sessionId }: Props) {
  const t = useTranslations("applications");
  const { user, loading: authLoading } = useAuth();
  const [claiming, setClaiming] = useState(false);
  const [claimed, setClaimed] = useState(false);
  const [error, setError] = useState(false);

  if (authLoading) return null;

  const token = getSessionToken(sessionId);
  if (!token || claimed) {
    return claimed ? (
      <div className="mx-auto mb-4 w-full max-w-xl rounded-xl border border-emerald-800 bg-emerald-950/40 p-3 text-center text-xs font-semibold text-emerald-300">
        {t("claimSuccess")}
      </div>
    ) : null;
  }

  const handleClaim = async () => {
    if (claiming) return;
    setClaiming(true);
    setError(false);
    try {
      await claimApplication(sessionId, token);
      removeSessionToken(sessionId);
      setClaimed(true);
    } catch {
      setError(true);
    } finally {
      setClaiming(false);
    }
  };

  return (
    <div className="mx-auto mb-4 w-full max-w-xl rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-xl">
      <p className="text-sm font-semibold text-slate-200">{t("claimPromptTitle")}</p>
      <p className="mt-1 text-xs text-slate-400">{t("claimPromptBody")}</p>
      {error && <p className="mt-2 text-xs text-rose-300">{t("claimError")}</p>}
      <div className="mt-3">
        {user ? (
          <button
            type="button"
            onClick={handleClaim}
            disabled={claiming}
            className="rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-500 px-4 py-2 text-xs font-bold text-white shadow shadow-indigo-500/20 transition hover:opacity-95 disabled:opacity-40"
          >
            {claiming ? t("resume") : t("claimButton")}
          </button>
        ) : (
          <Link
            href="/login"
            className="inline-block rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 transition hover:border-slate-500"
          >
            {t("loginToSave")}
          </Link>
        )}
      </div>
    </div>
  );
}
