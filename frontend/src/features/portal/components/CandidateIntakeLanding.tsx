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
      <div className="min-h-[60vh] flex flex-col items-center justify-center p-4">
        <div className="w-10 h-10 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm font-medium text-slate-600">Verifying secure candidate link...</p>
      </div>
    );
  }

  if (error || !intake) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center p-4 text-center max-w-md mx-auto">
        <div className="w-12 h-12 rounded-2xl bg-rose-100 text-rose-600 flex items-center justify-center mb-4">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h1 className="text-lg font-bold text-slate-900 mb-2">Invite Link Expired or Invalid</h1>
        <p className="text-xs text-slate-600 leading-relaxed mb-6">
          {error || "This single-use invite link is no longer valid. Please contact your relocation case manager to issue a fresh link."}
        </p>
        <button
          onClick={() => router.push("/")}
          className="rounded-xl bg-slate-900 px-5 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-slate-800 transition-colors"
        >
          Return to Homepage
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6 lg:px-8">
      <div className="rounded-3xl border border-slate-200/80 bg-white p-6 sm:p-10 shadow-xl shadow-slate-100">
        <div className="text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50/70 px-3.5 py-1 text-xs font-semibold text-indigo-700">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-600 animate-pulse" />
            Official Candidate Intake
          </div>
          <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
            {t("candidateWelcome")}
          </h1>
          <p className="mt-2 text-sm text-slate-600 leading-relaxed">
            Hello, <strong className="text-slate-900">{intake.candidate_name}</strong>! {t("candidateSubtitle")}
          </p>
        </div>

        <div className="mt-8 rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5">
          <div className="text-xs font-semibold text-indigo-900 uppercase tracking-wider mb-1">
            {t("assignedForm")}
          </div>
          <div className="text-base font-bold text-indigo-950">
            {intake.form_title}
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs text-indigo-700">
            <ShieldCheck className="w-4 h-4 shrink-0" />
            Pre-configured by your relocation coordinator for 100% official administrative compliance.
          </div>
        </div>

        <div className="mt-6">
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
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
                  className={`flex flex-col items-center justify-center p-3 rounded-xl border text-center transition-all ${
                    active
                      ? "border-indigo-600 bg-indigo-50/80 text-indigo-950 font-bold ring-2 ring-indigo-600/20"
                      : "border-slate-200 bg-white hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <span className="text-sm font-semibold">{lang.nativeName}</span>
                  <span className="text-[10px] text-slate-500">{lang.englishName}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-100 flex flex-col items-center gap-3">
          <button
            onClick={handleStartSession}
            disabled={starting}
            className="w-full rounded-2xl bg-indigo-600 py-3.5 text-sm font-bold text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-700 active:scale-[0.99] disabled:opacity-50 transition-all text-center"
          >
            {starting ? t("starting") : t("startAssistedSession")}
          </button>
          <p className="text-[11px] text-slate-400 text-center flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" />
            {t("securePrivateNotice")}
          </p>
        </div>
      </div>
    </div>
  );
}
