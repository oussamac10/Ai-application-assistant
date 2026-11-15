"use client";

import React, { useState } from "react";
import { useTranslations } from "next-intl";
import { Case } from "../types";
import { Check, Copy } from "lucide-react";

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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#060910]/80 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-lg rounded-2xl bg-[#0F1522] border border-white/10 text-slate-100 p-6 shadow-2xl sm:p-8">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
            <Check className="w-6 h-6" />
          </div>
          <h2 id="invite-headline" className="mt-3.5 text-lg font-bold text-white">
            {t("inviteModalTitle")}
          </h2>
          <p className="mt-1 text-xs text-slate-400 leading-relaxed max-w-sm mx-auto">
            {t("inviteModalSub")}
          </p>
        </div>

        <div className="mt-6 rounded-xl border border-white/10 bg-[#0A0E17] p-4 space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-slate-400 font-medium">Citizen / Applicant:</span>
            <span className="font-semibold text-white">{caseData.candidate_name}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-400 font-medium">Email:</span>
            <span className="text-slate-200">{caseData.candidate_email}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-slate-400 font-medium">Document:</span>
            <span className="text-emerald-400 font-semibold">{caseData.form_title}</span>
          </div>
        </div>

        <div className="mt-4">
          <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-1.5">
            Single-Use Intake Invite Link
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              readOnly
              value={inviteUrl}
              className="flex-1 rounded-xl border border-white/10 bg-[#0A0E17] px-3 py-2 text-xs font-mono text-slate-100 select-all focus:outline-none focus:border-emerald-500 focus-visible:ring-2 focus-visible:ring-emerald-500/30"
            />
            <button
              type="button"
              onClick={handleCopy}
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-bold shadow-2xs transition-all cursor-pointer ${
                copied
                  ? "bg-emerald-400 text-slate-950"
                  : "bg-emerald-500 text-slate-950 hover:bg-emerald-400"
              }`}
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  {t("copied")}
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
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
            className="w-full rounded-xl bg-[#151D2E] hover:bg-slate-800 border border-white/10 py-2.5 text-xs font-semibold text-white shadow-xs transition-colors cursor-pointer"
          >
            {t("done")}
          </button>
        </div>
      </div>
    </div>
  );
}
