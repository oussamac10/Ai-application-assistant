"use client";

import React, { useState } from "react";
import { useTranslations } from "next-intl";
import { Case } from "../types";

interface InviteSuccessModalProps {
  caseData: Case | null;
  onClose: () => void;
}

export function InviteSuccessModal({
  caseData,
  onClose,
}: InviteSuccessModalProps) {
  const t = useTranslations("portal");
  const [copied, setCopied] = useState(false);

  if (!caseData || !caseData.invite_token) return null;

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const inviteUrl = `${origin}/portal/invite/${caseData.invite_token}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Fallback
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="invite-headline"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl ring-1 ring-slate-900/10 sm:p-8">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-600">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 id="invite-headline" className="mt-3.5 text-lg font-bold text-slate-900">
            {t("inviteModalTitle")}
          </h2>
          <p className="mt-1 text-xs text-slate-500 leading-relaxed max-w-sm mx-auto">
            {t("inviteModalSub")}
          </p>
        </div>

        <div className="mt-6 rounded-xl border border-slate-100 bg-slate-50/80 p-4 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-slate-500 font-medium">Citizen / Applicant:</span>
            <span className="font-semibold text-slate-900">{caseData.candidate_name}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500 font-medium">Email:</span>
            <span className="text-slate-700">{caseData.candidate_email}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-500 font-medium">Document:</span>
            <span className="text-indigo-600 font-semibold">{caseData.form_title}</span>
          </div>
        </div>

        <div className="mt-4">
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
            Single-Use Intake Invite Link
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              readOnly
              value={inviteUrl}
              className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-mono text-slate-700 select-all focus:outline-none"
            />
            <button
              type="button"
              onClick={handleCopy}
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-semibold shadow-2xs transition-all ${
                copied
                  ? "bg-emerald-600 text-white"
                  : "bg-indigo-600 text-white hover:bg-indigo-700"
              }`}
            >
              {copied ? (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                  {t("copied")}
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
                    />
                  </svg>
                  {t("copyInvite")}
                </>
              )}
            </button>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="w-full rounded-xl bg-slate-900 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-slate-800 transition-colors"
          >
            {t("done")}
          </button>
        </div>
      </div>
    </div>
  );
}
