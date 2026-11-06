"use client";

import React, { useEffect, useRef } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { FileCheck, ShieldCheck, UserPlus, LogIn, X, Sparkles, CheckCircle2 } from "lucide-react";

interface ExportAccountGateModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
}

export function ExportAccountGateModal({
  isOpen,
  onClose,
  sessionId,
}: ExportAccountGateModalProps) {
  const t = useTranslations("complete");
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

  const redirectUrl = `/application/session/${sessionId}/complete`;
  const registerHref = `/register?redirect=${encodeURIComponent(redirectUrl)}`;
  const loginHref = `/login?redirect=${encodeURIComponent(redirectUrl)}`;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="export-gate-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-150"
    >
      <div
        ref={modalRef}
        className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 sm:p-7 shadow-2xl space-y-5 animate-in zoom-in-95 duration-150"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-600 shadow-2xs">
              <FileCheck className="h-6 w-6" />
            </div>
            <div>
              <div className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[10px] font-bold text-emerald-800 uppercase tracking-wider mb-1">
                <Sparkles className="w-3 h-3 text-emerald-600" />
                Answers Complete (100%)
              </div>
              <h2 id="export-gate-title" className="text-base font-bold text-slate-900">
                {t("exportGateTitle")}
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Value Proposition Box */}
        <div className="rounded-2xl border border-slate-100 bg-slate-50/80 p-4 space-y-2.5 text-start">
          <p className="text-xs text-slate-600 leading-relaxed">
            {t("exportGateSubtitle")}
          </p>

          <ul className="space-y-1.5 pt-1 text-xs text-slate-700 font-medium">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{t("exportGateBenefitPdf")}</span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{t("exportGateBenefitVault")}</span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{t("exportGateBenefitAccess")}</span>
            </li>
          </ul>
        </div>

        {/* Action Buttons */}
        <div className="space-y-2.5 pt-1">
          <Link
            href={registerHref}
            className="flex items-center justify-center gap-2 w-full rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white py-3 px-4 text-xs font-semibold shadow-xs hover:shadow-sm active:scale-[0.99] transition-all cursor-pointer"
          >
            <UserPlus className="h-4 w-4" />
            <span>{t("exportGateRegisterBtn")}</span>
          </Link>

          <Link
            href={loginHref}
            className="flex items-center justify-center gap-2 w-full rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 py-2.5 px-4 text-xs font-semibold transition-all cursor-pointer"
          >
            <LogIn className="h-4 w-4 text-slate-500" />
            <span>{t("exportGateLoginBtn")}</span>
          </Link>
        </div>

        {/* Trust Badges */}
        <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-500 pt-1 border-t border-slate-100">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
          <span>100% Free • No credit card required • GDPR compliant</span>
        </div>

        {/* Secondary Dismiss */}
        <div className="text-center pt-0.5">
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
          >
            {t("exportGateDismiss")}
          </button>
        </div>
      </div>
    </div>
  );
}
