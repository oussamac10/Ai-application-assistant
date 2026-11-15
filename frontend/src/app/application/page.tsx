"use client";

import React from "react";
import { useTranslations } from "next-intl";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import DocumentUploadForm from "@/features/document-upload/components/DocumentUploadForm";
import LanguageSelector from "@/features/form-session/components/LanguageSelector";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import { FileText, Lock } from "lucide-react";

export default function ApplicationLanding() {
  const t = useTranslations("landing");
  const tc = useTranslations("common");
  const ts = useTranslations("setup");
  const { locale, setLocale } = useLanguage();

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center bg-[#0A0E17] text-slate-100 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-6xl flex-1 flex flex-col justify-center py-2">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Form Setup Context Sidebar (desktop) */}
          <aside className="hidden lg:flex lg:col-span-4 flex-col gap-4 sticky top-20">
            {/* Overview Card */}
            <div className="surface-card rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  {ts("badge")}
                </span>
                <span className="text-xs font-mono text-slate-400 tabular-nums">{ts("stepOfFour")}</span>
              </div>

              <div>
                <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                  <FileText className="h-4 w-4 text-emerald-400" />
                  {ts("sidebarTitle")}
                </h2>
                <p className="mt-1.5 text-xs text-slate-400 leading-relaxed">
                  {ts("sidebarBody")}
                </p>
              </div>

              {/* Steps Progress Indicator */}
              <div className="space-y-2 border-t border-white/10 pt-3.5">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  {ts("journeyHeading")}
                </p>
                <div className="space-y-1.5 text-xs">
                  <div className="flex items-center gap-2.5 text-white font-semibold bg-emerald-500/15 p-2 rounded-lg border border-emerald-500/40 ring-1 ring-emerald-500/20">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-[10px] text-slate-950 font-bold tabular-nums">1</span>
                    <span>{ts("step1")}</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-400 px-2 py-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#151D2E] border border-white/10 text-[10px] text-slate-300 font-semibold tabular-nums">2</span>
                    <span>{ts("step2")}</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-400 px-2 py-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#151D2E] border border-white/10 text-[10px] text-slate-300 font-semibold tabular-nums">3</span>
                    <span>{ts("step3")}</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-400 px-2 py-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#151D2E] border border-white/10 text-[10px] text-slate-300 font-semibold tabular-nums">4</span>
                    <span>{ts("step4")}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Privacy Card */}
            <div className="rounded-xl border border-white/10 bg-[#0F1522] p-4 flex items-center gap-3 shadow-2xs">
              <div className="h-8 w-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
                <Lock className="h-4 w-4" />
              </div>
              <div className="text-xs text-slate-400 leading-snug">
                <span className="font-semibold text-white block">{ts("privacyCardTitle")}</span>
                {ts("privacyCardBody")}
              </div>
            </div>
          </aside>

          {/* Right Column: Main Setup Panel */}
          <div className="lg:col-span-8 flex flex-col justify-center w-full">
            <div className="surface-panel rounded-2xl p-6 sm:p-8">
              {/* Header */}
              <div className="text-center">
                <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  <span className="tabular-nums">{ts("headerBadge")}</span>
                </div>
                <h1 className="mt-3 text-2xl sm:text-3xl font-bold tracking-tight text-white">
                  {tc("title")}
                </h1>
                <p className="mt-1.5 text-sm text-slate-400">
                  {ts("subtitle")}
                </p>
              </div>

              <div className="mt-6 space-y-6">
                <LanguageSelector
                  selectedCode={locale}
                  onSelect={setLocale}
                  title={t("selectUiLanguage")}
                  subtitle={ts("languageSubtitle", { count: UNIVERSAL_LANGUAGES.length })}
                />
                <DocumentUploadForm currentLocale={locale} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
