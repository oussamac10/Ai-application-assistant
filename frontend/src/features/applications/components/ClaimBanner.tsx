"use client";

import { useEffect, useState, useRef } from "react";
import { useTranslations } from "next-intl";
import { Bookmark, ShieldCheck, Check, Sparkles, X } from "lucide-react";
import { useSafeAuth } from "@/features/auth/hooks/useSafeAuth";
import { claimApplication } from "../services/applicationsClient";
import {
  getSessionToken,
  removeSessionToken,
} from "@/features/form-session/services/sessionCredentials";
import { SaveAndResumeModal } from "./SaveAndResumeModal";

interface Props {
  sessionId: string;
  formTitle?: string;
  completedCount?: number;
  totalCount?: number;
  progressPercent?: number;
}

export default function ClaimBanner({
  sessionId,
  formTitle,
  completedCount = 0,
  totalCount = 0,
  progressPercent = 0,
}: Props) {
  const t = useTranslations("applications");
  const auth = useSafeAuth();
  const user = auth?.user ?? null;
  const authLoading = auth?.loading ?? false;
  const [claiming, setClaiming] = useState(false);
  const [claimed, setClaimed] = useState(false);
  const [error, setError] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const claimAttemptedRef = useRef(false);

  const token = getSessionToken(sessionId);

  // Auto-claim when an authenticated user arrives with a local anonymous token
  useEffect(() => {
    if (user && token && !claimed && !claimAttemptedRef.current) {
      claimAttemptedRef.current = true;
      setClaiming(true);
      claimApplication(sessionId, token)
        .then(() => {
          removeSessionToken(sessionId);
          setClaimed(true);
        })
        .catch(() => {
          setError(true);
        })
        .finally(() => {
          setClaiming(false);
        });
    }
  }, [user, token, claimed, sessionId]);

  if (authLoading || dismissed) return null;

  if (!token || claimed) {
    return claimed ? (
      <div className="mb-4 w-full rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-center text-xs font-semibold text-emerald-800 flex items-center justify-center gap-2">
        <Check className="w-4 h-4 text-emerald-600" />
        <span>{t("claimSuccess")}</span>
      </div>
    ) : null;
  }

  const handleManualClaim = async () => {
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
    <>
      <div className="mb-4 w-full rounded-2xl border border-indigo-200/90 bg-white p-3.5 sm:p-4 shadow-2xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-start">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 border border-indigo-200/80 text-indigo-600">
              <Bookmark className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <p className="text-xs font-bold text-slate-900">{t("claimPromptTitle")}</p>
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200/60 px-1.5 py-0.2 rounded-full">
                  <ShieldCheck className="w-3 h-3" />
                  Free
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">{t("claimPromptBody")}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
            {error && <span className="text-xs text-rose-700">{t("claimError")}</span>}
            {user ? (
              <button
                type="button"
                onClick={handleManualClaim}
                disabled={claiming}
                className="btn-primary px-3.5 py-1.5 text-xs font-semibold cursor-pointer"
              >
                {claiming ? t("resume") : t("claimButton")}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setIsModalOpen(true)}
                className="btn-primary inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold cursor-pointer shadow-xs"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{t("saveAndResume")}</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => setDismissed(true)}
              aria-label="Dismiss banner"
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <SaveAndResumeModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        sessionId={sessionId}
        formTitle={formTitle}
        completedCount={completedCount}
        totalCount={totalCount}
        progressPercent={progressPercent}
      />
    </>
  );
}
