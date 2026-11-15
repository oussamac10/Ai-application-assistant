"use client";

import React, { useEffect, useRef } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { BookmarkCheck, ShieldCheck, UserPlus, LogIn, X } from "lucide-react";

interface SaveAndResumeModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  formTitle?: string;
  completedCount?: number;
  totalCount?: number;
  progressPercent?: number;
}

export function SaveAndResumeModal({
  isOpen,
  onClose,
  sessionId,
  formTitle,
  completedCount = 0,
  totalCount = 0,
  progressPercent = 0,
}: SaveAndResumeModalProps) {
  const t = useTranslations("applications");
  const modalRef = useRef<HTMLDivElement>(null);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const redirectUrl = `/application/session/${sessionId}`;
  const registerHref = `/register?redirect=${encodeURIComponent(redirectUrl)}`;
  const loginHref = `/login?redirect=${encodeURIComponent(redirectUrl)}`;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="save-resume-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150 motion-reduce:animate-none"
    >
      <div
        ref={modalRef}
        className="w-full max-w-md rounded-3xl border border-white/10 bg-[#0F1522] p-6 sm:p-7 text-slate-100 shadow-2xl space-y-5 animate-in zoom-in-95 duration-150 motion-reduce:animate-none"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <BookmarkCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 id="save-resume-title" className="text-base font-bold text-white">
                {t("saveModalTitle")}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                {t("saveModalSubtitle")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("cancel")}
            className="rounded-full p-1.5 text-slate-400 hover:bg-white/10 hover:text-slate-200 transition-colors motion-reduce:transition-none"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Progress Snapshot Card */}
        <div className="rounded-2xl border border-white/[0.08] bg-[#0A0E17] p-4 space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-100 truncate max-w-[200px]">
              {formTitle || "Application Form"}
            </span>
            <span className="font-mono font-bold text-emerald-400">
              {progressPercent}%
            </span>
          </div>

          <div className="h-2 w-full rounded-full bg-[#151D2E] border border-white/[0.06] overflow-hidden">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all duration-300 motion-reduce:transition-none"
              style={{ width: `${Math.min(100, Math.max(5, progressPercent))}%` }}
            />
          </div>

          <p className="text-[11px] text-slate-400">
            {t("progressNotice", {
              completed: completedCount,
              total: totalCount,
              percent: progressPercent,
            })}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="space-y-2.5 pt-1">
          <Link
            href={registerHref}
            className="btn-primary w-full py-2.5 px-4 text-xs font-bold"
          >
            <UserPlus className="h-4 w-4" />
            <span>{t("createAccountToResume")}</span>
          </Link>

          <Link
            href={loginHref}
            className="btn-secondary w-full py-2.5 px-4 text-xs font-semibold"
          >
            <LogIn className="h-4 w-4 text-slate-400" />
            <span>{t("loginToResume")}</span>
          </Link>
        </div>

        {/* Trust Badges */}
        <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-400 pt-2 border-t border-white/[0.08]">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
          <span>{t("freeNotice")}</span>
        </div>

        {/* Secondary Dismiss */}
        <div className="text-center pt-1">
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors motion-reduce:transition-none cursor-pointer"
          >
            {t("continueAsGuest")}
          </button>
        </div>
      </div>
    </div>
  );
}
