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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-150"
    >
      <div
        ref={modalRef}
        className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 sm:p-7 shadow-2xl space-y-5 animate-in zoom-in-95 duration-150"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 border border-indigo-200/80 text-indigo-600 shadow-2xs">
              <BookmarkCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 id="save-resume-title" className="text-base font-bold text-slate-900">
                {t("saveModalTitle")}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {t("saveModalSubtitle")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("cancel")}
            className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Progress Snapshot Card */}
        <div className="rounded-2xl border border-slate-100 bg-slate-50/80 p-4 space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-800 truncate max-w-[200px]">
              {formTitle || "Application Form"}
            </span>
            <span className="font-mono font-bold text-indigo-600">
              {progressPercent}%
            </span>
          </div>

          <div className="h-2 w-full rounded-full bg-slate-200 overflow-hidden">
            <div
              className="h-full rounded-full bg-indigo-600 transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(5, progressPercent))}%` }}
            />
          </div>

          <p className="text-[11px] text-slate-500">
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
            className="flex items-center justify-center gap-2 w-full rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 px-4 text-xs font-semibold shadow-xs hover:shadow-sm active:scale-[0.99] transition-all"
          >
            <UserPlus className="h-4 w-4" />
            <span>{t("createAccountToResume")}</span>
          </Link>

          <Link
            href={loginHref}
            className="flex items-center justify-center gap-2 w-full rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 py-2.5 px-4 text-xs font-semibold transition-all"
          >
            <LogIn className="h-4 w-4 text-slate-500" />
            <span>{t("loginToResume")}</span>
          </Link>
        </div>

        {/* Trust Badges */}
        <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-500 pt-1 border-t border-slate-100">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
          <span>{t("freeNotice")}</span>
        </div>

        {/* Secondary Dismiss */}
        <div className="text-center pt-1">
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
          >
            {t("continueAsGuest")}
          </button>
        </div>
      </div>
    </div>
  );
}
