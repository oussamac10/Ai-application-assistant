"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useSafeAuth } from "@/features/auth/hooks/useSafeAuth";
import { claimApplication } from "../services/applicationsClient";
import {
  getSessionToken,
  removeSessionToken,
} from "@/features/form-session/services/sessionCredentials";

interface Props {
  sessionId: string;
}

export default function ClaimBanner({ sessionId }: Props) {
  const t = useTranslations("applications");
  const auth = useSafeAuth();
  const user = auth?.user ?? null;
  const authLoading = auth?.loading ?? false;
  const [claiming, setClaiming] = useState(false);
  const [claimed, setClaimed] = useState(false);
  const [error, setError] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  if (authLoading || dismissed) return null;

  const token = getSessionToken(sessionId);
  if (!token || claimed) {
    return claimed ? (
      <div className="mb-4 w-full rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-center text-xs font-semibold text-emerald-800">
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
    <div className="mb-4 w-full rounded-xl border border-indigo-200 bg-white p-3.5 sm:p-4 shadow-2xs">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-start">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-600">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold text-slate-900">{t("claimPromptTitle")}</p>
            <p className="text-xs text-slate-600">{t("claimPromptBody")}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
          {error && <span className="text-xs text-rose-700">{t("claimError")}</span>}
          {user ? (
            <button
              type="button"
              onClick={handleClaim}
              disabled={claiming}
              className="btn-primary px-3.5 py-1.5 text-xs font-semibold"
            >
              {claiming ? t("resume") : t("claimButton")}
            </button>
          ) : (
            <Link
              href="/login"
              className="btn-secondary px-3.5 py-1.5 text-xs font-medium"
            >
              {t("loginToSave")}
            </Link>
          )}
          <button
            type="button"
            onClick={() => setDismissed(true)}
            aria-label="Dismiss banner"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
