"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import { redeemCandidateInvite } from "../services/portalClient";
import { CandidateIntakeInfo } from "../types";
import { AlertCircle, ShieldCheck, Lock } from "lucide-react";

interface CandidateIntakeLandingProps {
  token: string;
}

export function CandidateIntakeLanding({ token }: CandidateIntakeLandingProps) {
  const t = useTranslations("portal");
  const router = useRouter();
  const { setLocale } = useLanguage();

  const [intake, setIntake] = useState<CandidateIntakeInfo | null>(null);
  const [selectedLang, setSelectedLang] = useState("en");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    redeemCandidateInvite(token)
      .then((data) => {
        setIntake(data);
        if (data.user_language) {
          setSelectedLang(data.user_language);
          setLocale(data.user_language);
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Invalid or expired invite link.");
      })
      .finally(() => setLoading(false));
  }, [token, setLocale]);

  const handleStartSession = () => {
    if (!intake) return;
    setStarting(true);
    setLocale(selectedLang);
    // Store ownership token in sessionStorage for session authentication
    try {
      sessionStorage.setItem(`session_token_${intake.session_id}`, intake.session_token);
    } catch {
      // Ignored in non-browser
    }
    // Route to the existing application session workflow
    router.push(`/application/session/${intake.session_id}`);
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] bg-[#0A0E17] text-slate-100 flex flex-col items-center justify-center p-4">
        <div className="w-10 h-10 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm font-medium text-slate-400">Verifying secure candidate link...</p>
      </div>
    );
  }

  if (error || !intake) {
    return (
      <div className="min-h-[60vh] bg-[#0A0E17] text-slate-100 flex flex-col items-center justify-center p-4 text-center">
        <div className="max-w-md mx-auto flex flex-col items-center">
          <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center justify-center mb-4">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h1 className="text-lg font-bold text-white mb-2">Invite Link Expired or Invalid</h1>
          <p className="text-xs text-slate-400 leading-relaxed mb-6">
            {error || "This single-use invite link is no longer valid. Please contact your relocation case manager to issue a fresh link."}
          </p>
          <button
            onClick={() => router.push("/")}
            className="rounded-xl bg-emerald-500 px-5 py-2.5 text-xs font-bold text-slate-950 shadow-xs hover:bg-emerald-400 transition-colors cursor-pointer"
          >
            Return to Homepage
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[75vh] bg-[#0A0E17] text-slate-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-2xl">
        <div className="rounded-3xl border border-white/10 bg-[#0F1522] p-6 sm:p-10 shadow-2xl">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-semibold text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Official Candidate Intake
            </div>
            <h1 className="mt-4 text-2xl font-bold tracking-tight text-white sm:text-3xl">
              {t("candidateWelcome")}
            </h1>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Hello, <strong className="text-white">{intake.candidate_name}</strong>! {t("candidateSubtitle")}
            </p>
          </div>

          <div className="mt-8 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5">
            <div className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-1">
              {t("assignedForm")}
            </div>
            <div className="text-base font-bold text-white">
              {intake.form_title}
            </div>
            <div className="mt-3 flex items-center gap-2 text-xs text-slate-300">
              <ShieldCheck className="w-4 h-4 shrink-0 text-emerald-400" />
              Pre-configured by your relocation coordinator for 100% official administrative compliance.
            </div>
          </div>

          <div className="mt-6">
            <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-2">
              {t("selectLangPrompt")}
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {UNIVERSAL_LANGUAGES.map((lang) => {
                const active = selectedLang === lang.code;
                return (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => setSelectedLang(lang.code)}
                    className={`flex flex-col items-center justify-center p-3 rounded-xl border text-center transition-all cursor-pointer ${
                      active
                        ? "border-emerald-500 bg-emerald-500/15 text-emerald-300 font-bold ring-2 ring-emerald-500/30"
                        : "border-white/10 bg-[#0A0E17] hover:bg-[#151D2E] hover:border-white/20 text-slate-200"
                    }`}
                  >
                    <span className="text-sm font-semibold">{lang.nativeName}</span>
                    <span className={`text-[10px] ${active ? "text-emerald-300/80" : "text-slate-400"}`}>
                      {lang.englishName}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-white/[0.08] flex flex-col items-center gap-3">
            <button
              onClick={handleStartSession}
              disabled={starting}
              className="w-full rounded-2xl bg-emerald-500 py-3.5 text-sm font-bold text-slate-950 shadow-[0_0_24px_-4px_rgba(16,185,129,0.4)] hover:bg-emerald-400 active:scale-[0.99] disabled:opacity-50 transition-all text-center cursor-pointer"
            >
              {starting ? t("starting") : t("startAssistedSession")}
            </button>
            <p className="text-[11px] text-slate-400 text-center flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-slate-500" />
              {t("securePrivateNotice")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
