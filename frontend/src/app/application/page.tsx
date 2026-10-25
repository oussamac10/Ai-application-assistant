"use client";

import React from "react";
import { useTranslations } from "next-intl";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import DocumentUploadForm from "@/features/document-upload/components/DocumentUploadForm";
import LanguageSelector from "@/features/form-session/components/LanguageSelector";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";

export default function ApplicationLanding() {
  const t = useTranslations("landing");
  const tc = useTranslations("common");
  const { locale, setLocale } = useLanguage();

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-6xl flex-1 flex flex-col justify-center py-2">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Form Setup Context Sidebar (desktop) */}
          <aside className="hidden lg:flex lg:col-span-4 flex-col gap-4 sticky top-20">
            {/* Overview Card */}
            <div className="surface-card rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
                  Application Setup
                </span>
                <span className="text-xs font-mono text-slate-500 tabular-nums">Step 1 of 4</span>
              </div>

              <div>
                <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                  <svg className="h-4 w-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Universal Form Assistant
                </h2>
                <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
                  Complete any official form in your native language. Upload your PDF document to extract questions and fill it step by step.
                </p>
              </div>

              {/* Steps Progress Indicator */}
              <div className="space-y-2 border-t border-slate-200 pt-3.5">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Application Journey
                </p>
                <div className="space-y-1.5 text-xs">
                  <div className="flex items-center gap-2.5 text-indigo-900 font-semibold bg-indigo-50 p-2 rounded-lg border border-indigo-200">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600 text-[10px] text-white font-semibold tabular-nums">1</span>
                    <span>Language & Document Upload</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-600 px-2 py-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 border border-slate-300 text-[10px] text-slate-600 font-semibold tabular-nums">2</span>
                    <span>Guided Questions & AI Normalization</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-600 px-2 py-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 border border-slate-300 text-[10px] text-slate-600 font-semibold tabular-nums">3</span>
                    <span>Final Review & Confirmation</span>
                  </div>
                  <div className="flex items-center gap-2.5 text-slate-600 px-2 py-1.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 border border-slate-300 text-[10px] text-slate-600 font-semibold tabular-nums">4</span>
                    <span>Signed Official PDF Export</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Privacy Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 flex items-center gap-3 shadow-2xs">
              <div className="h-8 w-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 shrink-0">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <div className="text-xs text-slate-600 leading-snug">
                <span className="font-semibold text-slate-900 block">Zero-Retention Privacy</span>
                Original answers are preserved and protected by cryptographic session tokens.
              </div>
            </div>
          </aside>

          {/* Right Column: Main Setup Panel */}
          <div className="lg:col-span-8 flex flex-col justify-center w-full">
            <div className="surface-panel rounded-2xl p-6 sm:p-8">
              {/* Header */}
              <div className="text-center">
                <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
                  <span className="tabular-nums">Step 1 of 4 • Universal Form Setup</span>
                </div>
                <h1 className="mt-3 text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                  {tc("title")}
                </h1>
                <p className="mt-1.5 text-sm text-slate-600">
                  Choose your native language and upload your PDF form to begin
                </p>
              </div>

              <div className="mt-6 space-y-6">
                <LanguageSelector
                  selectedCode={locale}
                  onSelect={setLocale}
                  title={t("selectUiLanguage")}
                  subtitle={`Questions and explanations will be shown in your language (${UNIVERSAL_LANGUAGES.length} languages available).`}
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
