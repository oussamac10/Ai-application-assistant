"use client";

import React, { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Case } from "../types";
import {
  Check,
  Copy,
  ExternalLink,
  FileText,
  Link2,
  Mail,
  ShieldCheck,
  User,
  X,
} from "lucide-react";

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

  useEffect(() => {
    if (!caseData || !caseData.invite_token) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [caseData, onClose]);

  if (!caseData || !caseData.invite_token) return null;

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const inviteUrl = `${origin}/portal/invite/${caseData.invite_token}`;
  const formLabel = caseData.form_title ?? "Official Form";
  const mailSubject = encodeURIComponent(`Form invitation: ${formLabel}`);
  const mailBody = encodeURIComponent(
    `Hello ${caseData.candidate_name},\n\nPlease complete the form "${formLabel}" using this personal link:\n${inviteUrl}`
  );
  const mailtoHref = `mailto:${caseData.candidate_email}?subject=${mailSubject}&body=${mailBody}`;

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
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#060910]/80 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-xl rounded-3xl bg-[#0F1522] border border-white/10 text-slate-100 p-6 sm:p-7 shadow-2xl space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3.5 min-w-0">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
              <Check className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h2
                id="invite-headline"
                className="text-lg font-bold text-white leading-tight"
              >
                {t("inviteModalTitle")}
              </h2>
              <p className="mt-1 text-xs text-slate-400 leading-relaxed">
                {t("inviteModalSub")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="shrink-0 rounded-xl p-1.5 text-slate-400 hover:bg-[#151D2E] hover:text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#0A0E17] divide-y divide-white/[0.08]">
          <div className="p-4 flex items-start gap-3.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/[0.04] border border-white/10 text-slate-400">
              <User className="w-4 h-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-medium text-slate-400">Applicant</p>
              <p className="mt-0.5 text-sm font-semibold text-white break-words">
                {caseData.candidate_name}
              </p>
              <p
                className="mt-0.5 text-xs text-slate-400 break-all"
                dir="ltr"
              >
                {caseData.candidate_email}
              </p>
            </div>
          </div>

          <div className="p-4 flex items-start gap-3.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/[0.04] border border-white/10 text-slate-400">
              <FileText className="w-4 h-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-medium text-slate-400">
                Assigned form
              </p>
              <p className="mt-0.5 text-sm font-semibold text-slate-100 leading-snug break-words">
                {caseData.form_title}
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <label
            htmlFor="citizen-invite-url-input"
            className="block text-xs font-semibold text-slate-200"
          >
            Personal invite link
          </label>
          <div className="flex items-center gap-2 rounded-2xl border border-white/10 bg-[#0A0E17] p-1.5 pl-3.5 focus-within:border-emerald-500 focus-within:ring-2 focus-within:ring-emerald-500/20 transition-all">
            <Link2 className="w-4 h-4 text-slate-400 shrink-0" />
            <input
              id="citizen-invite-url-input"
              type="text"
              readOnly
              dir="ltr"
              value={inviteUrl}
              onFocus={(e) => e.currentTarget.select()}
              className="min-w-0 flex-1 bg-transparent py-1.5 text-xs font-mono text-slate-100 focus:outline-none select-all"
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
          <p className="flex items-start gap-2 text-[11px] text-slate-400 leading-relaxed px-0.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
            <span>
              Single-use link. The applicant can complete the form in their
              chosen language without creating an account.
            </span>
          </p>
        </div>

        <div className="pt-2 border-t border-white/[0.08] flex flex-col-reverse sm:flex-row sm:items-center sm:justify-between gap-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <a
              href={mailtoHref}
              className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-white/10 bg-[#0A0E17] hover:bg-[#151D2E] px-3.5 py-2 text-xs font-semibold text-slate-200 transition-colors"
            >
              <Mail className="w-3.5 h-3.5" />
              Send by Email
            </a>
            <a
              href={inviteUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-white/10 bg-[#0A0E17] hover:bg-[#151D2E] px-3.5 py-2 text-xs font-semibold text-slate-200 transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Open Preview
            </a>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center justify-center rounded-xl bg-[#151D2E] hover:bg-slate-800 border border-white/10 px-5 py-2 text-xs font-semibold text-white shadow-xs transition-colors cursor-pointer"
          >
            {t("done")}
          </button>
        </div>
      </div>
    </div>
  );
}
