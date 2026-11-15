"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowRight,
  Building2,
  CheckCircle2,
  FileText,
  Globe,
  Info,
  Loader2,
  Lock,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import { createSession, ApiError } from "@/features/form-session/services/apiClient";
import { setSessionToken } from "@/features/form-session/services/sessionCredentials";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import { getPublicFormByIdentifier } from "@/features/portal/services/portalClient";
import { PublicFormDetail } from "@/features/portal/types";

export default function ShortLinkIntakePage() {
  const params = useParams();
  const router = useRouter();
  const { locale, setLocale } = useLanguage();

  const slugParam = params?.slug;
  const identifier = Array.isArray(slugParam) ? slugParam.join("/") : slugParam || "";

  const [form, setForm] = useState<PublicFormDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedLanguage, setSelectedLanguage] = useState(locale || "en");
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  useEffect(() => {
    if (locale) {
      setSelectedLanguage(locale);
    }
  }, [locale]);

  useEffect(() => {
    if (!identifier) {
      setError("No form identifier provided.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    getPublicFormByIdentifier(identifier)
      .then((data) => {
        setForm(data);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Public form could not be loaded.");
      })
      .finally(() => setLoading(false));
  }, [identifier]);

  const handleStart = async () => {
    if (!form) return;
    try {
      setIsStarting(true);
      setStartError(null);

      const outputLang =
        form.supported_output_languages?.[0] || form.source_language || "de";

      setLocale(selectedLanguage);

      const session = await createSession(
        form.active_version_id,
        selectedLanguage,
        outputLang
      );

      if (session.ownershipToken) {
        setSessionToken(session.publicId, session.ownershipToken);
        try {
          sessionStorage.setItem(`session_token_${session.publicId}`, session.ownershipToken);
        } catch {
          // Non-browser fallback
        }
      }

      router.push(`/application/session/${session.publicId}`);
    } catch (err: unknown) {
      let msg = "Failed to start form session. Please try again.";
      if (err instanceof ApiError && err.detail && err.detail !== "unknown") {
        msg = err.detail;
      } else if (err instanceof Error && err.message && err.message !== "unknown") {
        msg = err.message;
      }
      setStartError(msg);
      setIsStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0E17] text-slate-100 flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-10 h-10 text-emerald-400 animate-spin" />
        <p className="text-sm font-medium text-slate-400">
          Loading official form intake...
        </p>
      </div>
    );
  }

  if (error || !form) {
    return (
      <div className="min-h-screen bg-[#0A0E17] text-slate-100 flex flex-col items-center justify-center p-6 text-center">
        <div className="max-w-md mx-auto flex flex-col items-center">
          <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center justify-center mb-4">
            <FileText className="w-7 h-7" />
          </div>
          <h2 className="text-xl font-bold text-white">Form Not Available</h2>
          <p className="text-sm text-slate-400 mt-2 mb-6">
            {error || "The requested official form could not be found or has not been published yet."}
          </p>
          <Link
            href="/organizations"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-500 text-slate-950 font-bold text-sm shadow-sm hover:bg-emerald-400 transition-colors"
          >
            <Search className="w-4 h-4" /> Browse Authority Directory
          </Link>
        </div>
      </div>
    );
  }

  const org = form.organization;
  const currentLangObj = UNIVERSAL_LANGUAGES.find((l) => l.code === selectedLanguage);

  return (
    <div className="min-h-screen bg-[#0A0E17] text-slate-100 py-10 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Authority Breadcrumb Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-[#0F1522] p-4 rounded-2xl border border-white/10 shadow-2xs">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-white">
                  {org?.name || "Official Public Authority"}
                </span>
                {org?.is_verified_government && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/30">
                    <ShieldCheck className="w-3 h-3 text-emerald-400" />
                    Verified
                  </span>
                )}
              </div>
              {org?.slug && (
                <Link
                  href={`/organizations/${org.slug}`}
                  className="text-[11px] text-emerald-400 hover:text-emerald-300 font-medium"
                >
                  View Official Portal →
                </Link>
              )}
            </div>
          </div>

          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>100% Free for Citizens</span>
          </div>
        </div>

        {/* Main Intake Form Card */}
        <div className="bg-[#0F1522] rounded-3xl border border-white/10 shadow-2xl p-6 sm:p-8 space-y-6">
          {startError && (
            <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-200 text-sm flex items-center justify-between">
              <span>{startError}</span>
              <button
                onClick={() => setStartError(null)}
                className="text-rose-400 hover:text-rose-300 font-bold ml-4 cursor-pointer"
              >
                ✕
              </button>
            </div>
          )}

          {/* Form Meta Badges */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              Official Form
            </span>
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-[#151D2E] border border-white/10 text-slate-300">
              {form.fields_count} Questions
            </span>
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-[#151D2E] border border-white/10 text-slate-300 capitalize">
              {form.category}
            </span>
          </div>

          {/* Title & Instructions */}
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight break-words">
              {form.name}
            </h1>
            {form.description && (
              <p className="mt-3 text-sm text-slate-300 leading-relaxed">
                {form.description}
              </p>
            )}
          </div>

          {/* Multilingual Guidance Notice */}
          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 flex items-start gap-3 shadow-2xs">
            <Sparkles className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-300 space-y-1">
              <span className="font-bold text-white">
                Multilingual Smartphone Intake:
              </span>
              <p className="text-slate-300">
                You can answer every question in your native language. The assistant will guide you step-by-step, normalize your entries, and produce an official ready-to-submit document adhering to German administrative standards.
              </p>
            </div>
          </div>

          {/* Required Documents Checklist */}
          {form.required_documents && form.required_documents.length > 0 && (
            <div className="rounded-2xl border border-white/10 bg-[#0A0E17] p-4 space-y-2">
              <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <Info className="w-4 h-4 text-emerald-400" />
                Required Supporting Documents to Have Ready:
              </span>
              <ul className="space-y-1.5 pt-1">
                {form.required_documents.map((doc, idx) => (
                  <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0 mt-1.5" />
                    <span>{doc}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Language Selection Section */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                <Globe className="w-4 h-4 text-slate-400" />
                Select Your Native Language:
              </label>
              <span className="text-xs font-semibold text-emerald-400">
                {currentLangObj?.nativeName} ({currentLangObj?.code.toUpperCase()})
              </span>
            </div>

            {/* Quick-choice Pill Buttons */}
            <div className="flex flex-wrap gap-2">
              {UNIVERSAL_LANGUAGES.slice(0, 8).map((lang) => {
                const isActive = selectedLanguage === lang.code;
                return (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => {
                      setSelectedLanguage(lang.code);
                      setLocale(lang.code);
                    }}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                      isActive
                        ? "bg-emerald-500 text-slate-950 font-bold shadow-xs"
                        : "bg-[#0A0E17] text-slate-200 hover:bg-[#151D2E] border border-white/10"
                    }`}
                  >
                    <span className="font-mono text-[10px] uppercase opacity-75">{lang.code}</span>
                    <span>{lang.nativeName}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Large Primary Action Button */}
          <div className="pt-4 border-t border-white/[0.08]">
            <button
              type="button"
              disabled={isStarting}
              onClick={handleStart}
              className="w-full flex items-center justify-center gap-2.5 py-4 px-6 rounded-2xl bg-emerald-500 hover:bg-emerald-400 active:scale-[0.99] text-slate-950 text-base font-bold shadow-[0_0_24px_-4px_rgba(16,185,129,0.4)] transition-all disabled:opacity-50 cursor-pointer"
            >
              {isStarting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Preparing Your Questions...</span>
                </>
              ) : (
                <>
                  <span>
                    Start in {currentLangObj?.nativeName || selectedLanguage.toUpperCase()}
                  </span>
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </div>

          {/* Trust Guarantees */}
          <div className="flex flex-wrap items-center justify-center gap-4 text-[11px] text-slate-400 pt-2">
            <span className="flex items-center gap-1">
              <Lock className="w-3.5 h-3.5 text-slate-500" />
              Cryptographically Protected Session
            </span>
            <span>•</span>
            <span>No Account Required</span>
            <span>•</span>
            <span>Official PDF Export</span>
          </div>
        </div>
      </div>
    </div>
  );
}
