"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import { getPublishedForms, createSession, PublishedForm } from "@/features/form-session/services/apiClient";
import { setSessionToken } from "@/features/form-session/services/sessionCredentials";
import DocumentUploadForm from "@/features/document-upload/components/DocumentUploadForm";
import LanguageSelector from "@/features/form-session/components/LanguageSelector";
import {
  UNIVERSAL_LANGUAGES,
  getLanguageByCode,
} from "@/features/form-session/utils/languages";
import {
  DOCUMENT_CATEGORIES,
  ISSUING_COUNTRIES,
  DocumentCategoryKey,
  getFormCatalogMeta,
} from "@/features/form-session/utils/formCatalogMetadata";

export default function ApplicationLanding() {
  const router = useRouter();
  const t = useTranslations("landing");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const { locale, setLocale } = useLanguage();

  const [forms, setForms] = useState<PublishedForm[]>([]);
  const [selectedFormId, setSelectedFormId] = useState<string>("");
  const [outputLanguage, setOutputLanguage] = useState<string>("en");
  const [privacyAccepted, setPrivacyAccepted] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [mode, setMode] = useState<"upload" | "manual">("upload");

  // Catalog Filters for "Select Manually"
  const [filterDocLanguage, setFilterDocLanguage] = useState<string>("all");
  const [filterCategory, setFilterCategory] = useState<DocumentCategoryKey>("all");
  const [filterCountry, setFilterCountry] = useState<string>("all");
  const [expandedPreviewId, setExpandedPreviewId] = useState<string | null>(null);

  useEffect(() => {
    async function loadForms() {
      try {
        setErrorMsg(null);
        const data = await getPublishedForms();
        setForms(data);
        if (data.length > 0) {
          setSelectedFormId(data[0].id);
        }
      } catch (err: any) {
        setErrorMsg(te(err.message) || "Failed to load forms list. Please retry.");
      } finally {
        setLoading(false);
      }
    }
    loadForms();
  }, [te]);

  const enrichedForms = useMemo(
    () =>
      forms.map((form) => ({
        form,
        meta: getFormCatalogMeta(form),
      })),
    [forms]
  );

  const filteredForms = useMemo(() => {
    return enrichedForms.filter(({ form, meta }) => {
      if (
        filterDocLanguage !== "all" &&
        form.sourceLanguage !== filterDocLanguage &&
        !form.supportedOutputLanguages.includes(filterDocLanguage)
      ) {
        return false;
      }
      if (filterCategory !== "all" && meta.categoryKey !== filterCategory) {
        return false;
      }
      if (
        filterCountry !== "all" &&
        meta.countryCode !== filterCountry &&
        meta.countryCode !== "INT"
      ) {
        return false;
      }
      return true;
    });
  }, [enrichedForms, filterDocLanguage, filterCategory, filterCountry]);

  const selectedForm = forms.find((f) => f.id === selectedFormId);
  const selectedFormMeta = useMemo(
    () => (selectedForm ? getFormCatalogMeta(selectedForm) : null),
    [selectedForm]
  );

  useEffect(() => {
    if (selectedForm) {
      if (!selectedForm.supportedOutputLanguages.includes(outputLanguage)) {
        setOutputLanguage(selectedForm.supportedOutputLanguages[0] || "en");
      }
    }
  }, [selectedForm, outputLanguage]);

  const handleStartSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFormId || !privacyAccepted || submitting) return;

    try {
      setSubmitting(true);
      setErrorMsg(null);

      const session = await createSession(selectedFormId, locale, outputLanguage);

      if (session.ownershipToken) {
        setSessionToken(session.publicId, session.ownershipToken);
      }

      router.push(`/application/session/${session.publicId}`);
    } catch (err: any) {
      setErrorMsg(te(err.message) || "An unexpected error occurred. Please try again.");
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center text-slate-900">
        <div className="flex flex-col items-center gap-3">
          <div className="h-9 w-9 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600" />
          <p className="text-sm font-medium text-slate-600">{tc("loading")}</p>
        </div>
      </main>
    );
  }

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
                  Complete any official form in your native language. Upload any PDF document or browse the categorized official form catalog with live document previews.
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
                    <span>Language & Document Selection</span>
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

            {/* Selected Template Preview Card when in manual mode */}
            {selectedForm && selectedFormMeta && mode === "manual" && (
              <div className="surface-card rounded-2xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-700">
                    Active Document Template
                  </span>
                  <span className="text-[11px] font-mono text-slate-600 rounded-md bg-slate-100 border border-slate-200 px-1.5 py-0.5 tabular-nums">
                    {selectedFormMeta.formCode} • v{selectedForm.versionNumber}
                  </span>
                </div>
                <p className="text-sm font-bold text-slate-900">{selectedForm.name}</p>
                <div className="flex flex-wrap gap-1.5 text-[11px]">
                  <span className="rounded-md bg-slate-100 border border-slate-200 px-2 py-0.5 font-medium text-slate-700">
                    {selectedFormMeta.countryCode} • {selectedFormMeta.countryName}
                  </span>
                  <span className="rounded-md bg-indigo-50 border border-indigo-200 px-2 py-0.5 font-medium text-indigo-700">
                    {selectedFormMeta.categoryLabel}
                  </span>
                </div>
                {selectedForm.description && (
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {selectedForm.description}
                  </p>
                )}
                <div className="flex items-center justify-between border-t border-slate-200 pt-2.5 text-[11px] text-slate-600">
                  <div>
                    <span>Questions in: </span>
                    <span className="font-bold text-indigo-700">
                      {getLanguageByCode(locale).nativeName}
                    </span>
                  </div>
                  <div>
                    <span>PDF Output: </span>
                    <span className="font-bold text-slate-900">
                      {getLanguageByCode(outputLanguage).nativeName}
                    </span>
                  </div>
                </div>
              </div>
            )}

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
                  Choose your native language and either upload any PDF form or select an official categorized template
                </p>
              </div>

              {/* Tab Selector */}
              <div className="mt-7 flex rounded-xl bg-slate-100 p-1 border border-slate-200">
                <button
                  type="button"
                  className={`flex-1 rounded-lg py-2.5 text-sm font-semibold transition-all duration-150 ${
                    mode === "upload"
                      ? "bg-white text-indigo-700 border border-slate-200/80 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                  onClick={() => setMode("upload")}
                >
                  {t("tabUpload") || "Upload Any PDF Form"}
                </button>
                <button
                  type="button"
                  className={`flex-1 rounded-lg py-2.5 text-sm font-semibold transition-all duration-150 ${
                    mode === "manual"
                      ? "bg-white text-indigo-700 border border-slate-200/80 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                  onClick={() => setMode("manual")}
                >
                  {t("tabManual") || "Select Manually"}
                </button>
              </div>

              {mode === "upload" ? (
                <div className="mt-6 space-y-6">
                  <LanguageSelector
                    selectedCode={locale}
                    onSelect={setLocale}
                    title={t("selectUiLanguage")}
                    subtitle={`Questions and explanations will be shown in your language (${UNIVERSAL_LANGUAGES.length} languages available).`}
                  />
                  <DocumentUploadForm currentLocale={locale} />
                </div>
              ) : (
                <form onSubmit={handleStartSession} className="mt-6 space-y-6">
                  {errorMsg && (
                    <div
                      role="alert"
                      className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 flex items-center gap-3"
                    >
                      <svg className="h-4 w-4 text-rose-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <span>{errorMsg}</span>
                    </div>
                  )}

                  {/* 1. Universal Searchable Language Studio */}
                  <LanguageSelector
                    selectedCode={locale}
                    onSelect={setLocale}
                    title={t("selectUiLanguage")}
                    subtitle={`Questions and explanations will be shown in your language (${UNIVERSAL_LANGUAGES.length} languages available).`}
                  />

                  {/* 2. Categorized Document Catalog with Pill Filters & Miniature PDF Preview */}
                  <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 sm:p-5 shadow-2xs">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                      <div>
                        <label htmlFor="form-select" className="block text-xs font-bold uppercase tracking-wider text-slate-800">
                          {t("selectForm")}
                        </label>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Filter official templates by document language, category, or issuing country and inspect the PDF layout preview.
                        </p>
                      </div>
                      <span className="rounded-full bg-indigo-50 border border-indigo-200 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
                        {filteredForms.length} {filteredForms.length === 1 ? "Document" : "Documents"}
                      </span>
                    </div>

                    {/* Interactive Pill Filter Bar: 1. Form Language, 2. Document Category, 3. Issuing Country */}
                    <div className="space-y-3 rounded-xl border border-slate-200/80 bg-slate-50/70 p-3.5">
                      {/* Filter 1: Document Language Pills */}
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 me-1">
                          1. Document Language:
                        </span>
                        {[
                          { code: "all", label: "All" },
                          { code: "en", label: "English · EN" },
                          { code: "de", label: "Deutsch · DE" },
                          { code: "fr", label: "Français · FR" },
                          { code: "ar", label: "العربية · AR" },
                        ].map((item) => {
                          const active = filterDocLanguage === item.code;
                          return (
                            <button
                              key={item.code}
                              type="button"
                              aria-label={`Filter document language: ${item.label}`}
                              onClick={() => setFilterDocLanguage(item.code)}
                              className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors ${
                                active
                                  ? "bg-indigo-600 text-white shadow-2xs"
                                  : "bg-white border border-slate-200 text-slate-600 hover:border-slate-300 hover:text-slate-900"
                              }`}
                            >
                              {item.label}
                            </button>
                          );
                        })}
                      </div>

                      {/* Filter 2: Document Category Pills */}
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 me-1">
                          2. Document Type:
                        </span>
                        {DOCUMENT_CATEGORIES.map((cat) => {
                          const active = filterCategory === cat.key;
                          return (
                            <button
                              key={cat.key}
                              type="button"
                              aria-label={`Filter document category: ${cat.label}`}
                              onClick={() => setFilterCategory(cat.key)}
                              className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors ${
                                active
                                  ? "bg-indigo-600 text-white shadow-2xs"
                                  : "bg-white border border-slate-200 text-slate-600 hover:border-slate-300 hover:text-slate-900"
                              }`}
                            >
                              {cat.label}
                            </button>
                          );
                        })}
                      </div>

                      {/* Filter 3: Issuing Country Pills */}
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 me-1">
                          3. Issuing Country:
                        </span>
                        {ISSUING_COUNTRIES.map((country) => {
                          const active = filterCountry === country.code;
                          return (
                            <button
                              key={country.code}
                              type="button"
                              aria-label={`Filter issuing country: ${country.name}`}
                              onClick={() => setFilterCountry(country.code)}
                              className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors ${
                                active
                                  ? "bg-indigo-600 text-white shadow-2xs"
                                  : "bg-white border border-slate-200 text-slate-600 hover:border-slate-300 hover:text-slate-900"
                              }`}
                            >
                              {country.code === "all"
                                ? "All Countries"
                                : `${country.code} · ${country.name.split(" (")[0]}`}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Accessible select element synchronized with cards */}
                    {forms.length === 0 ? (
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center text-sm text-slate-600">
                        No forms currently available.
                      </div>
                    ) : (
                      <>
                        <select
                          id="form-select"
                          className="sr-only"
                          value={selectedFormId}
                          onChange={(e) => setSelectedFormId(e.target.value)}
                        >
                          {forms.map((f) => (
                            <option key={f.id} value={f.id}>
                              {f.name} (v{f.versionNumber})
                            </option>
                          ))}
                        </select>

                        {/* Interactive Visual Form Cards with Miniature PDF Previews */}
                        <div className="space-y-3 pt-1">
                          {filteredForms.map(({ form: f, meta }) => {
                            const isSelected = f.id === selectedFormId;
                            const isExpanded = expandedPreviewId === f.id;
                            return (
                              <div
                                key={f.id}
                                onClick={() => setSelectedFormId(f.id)}
                                className={`group cursor-pointer rounded-xl border p-4 transition-all duration-150 ${
                                  isSelected
                                    ? "border-indigo-600 bg-indigo-50/40 ring-2 ring-indigo-600/15 shadow-xs"
                                    : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/60"
                                }`}
                              >
                                <div className="flex flex-col sm:flex-row gap-4 items-start">
                                  {/* Miniature PDF Sheet Visual Thumbnail */}
                                  <div
                                    aria-hidden="true"
                                    className="w-full sm:w-32 shrink-0 rounded-lg border border-slate-300 bg-white p-2.5 shadow-xs flex flex-col justify-between min-h-[136px] relative overflow-hidden"
                                  >
                                    <div>
                                      <div className="flex items-center justify-between border-b border-slate-200 pb-1 mb-1.5">
                                        <span className="font-mono text-[8px] font-bold uppercase tracking-tighter text-indigo-700 bg-indigo-50 px-1 py-0.2 rounded">
                                          {meta.formCode}
                                        </span>
                                        <span className="font-mono text-[8px] font-semibold uppercase text-slate-500">
                                          {f.sourceLanguage.toUpperCase()} PDF
                                        </span>
                                      </div>
                                      <div className="h-1.5 w-3/4 rounded-full bg-slate-800 mb-2" />

                                      <div className="space-y-1.5">
                                        {meta.previewSections.slice(0, 3).map((sec, idx) => (
                                          <div
                                            key={idx}
                                            className="rounded border border-slate-200 bg-slate-50 px-1.5 py-1"
                                          >
                                            <div className="text-[7px] font-semibold text-slate-600 truncate">
                                              {sec.sectionTitle}
                                            </div>
                                            <div className="mt-0.5 flex gap-1">
                                              <div className="h-1 flex-1 rounded bg-slate-300" />
                                              <div className="h-1 w-1/3 rounded bg-indigo-200" />
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>

                                    <div className="mt-2 pt-1 border-t border-dashed border-slate-200 flex items-center justify-between">
                                      <span className="text-[7px] font-mono uppercase text-slate-400">
                                        {meta.countryCode} OFFICIAL
                                      </span>
                                      {meta.hasSignatureBox && (
                                        <span className="rounded border border-amber-300 bg-amber-50 px-1 text-[7px] font-mono font-semibold text-amber-800">
                                          SIGN
                                        </span>
                                      )}
                                    </div>
                                  </div>

                                  {/* Form Card Details & Taxonomy */}
                                  <div className="flex-1 min-w-0 space-y-2 w-full">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                      <div className="flex flex-wrap items-center gap-1.5">
                                        <span className="inline-flex items-center rounded-md bg-slate-100 border border-slate-200 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                                          {meta.countryCode} • {meta.countryName}
                                        </span>
                                        <span className="inline-flex items-center rounded-md bg-indigo-50 border border-indigo-200 px-2 py-0.5 text-[11px] font-semibold text-indigo-700">
                                          {meta.categoryLabel}
                                        </span>
                                        <span className="inline-flex items-center rounded-md bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[11px] font-medium text-emerald-800">
                                          ~{meta.estimatedMinutes} min • {meta.fieldCount} fields
                                        </span>
                                      </div>
                                      <span
                                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                                          isSelected
                                            ? "bg-indigo-600 text-white"
                                            : "bg-slate-100 text-slate-600"
                                        }`}
                                      >
                                        {isSelected ? "Selected" : "Select"}
                                      </span>
                                    </div>

                                    <div>
                                      <h3 className="text-base font-bold text-slate-900">
                                        {f.name}{" "}
                                        <span className="text-xs font-mono font-normal text-slate-500">
                                          (v{f.versionNumber})
                                        </span>
                                      </h3>
                                      <p className="text-xs text-slate-500 font-medium">
                                        Issuing Authority: {meta.authority}
                                      </p>
                                    </div>

                                    {f.description && (
                                      <p className="text-xs text-slate-600 leading-relaxed">
                                        {f.description}
                                      </p>
                                    )}

                                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                                      <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-600">
                                        <span className="font-medium">Supported PDF Output:</span>
                                        {f.supportedOutputLanguages.map((langCode) => {
                                          const info = getLanguageByCode(langCode);
                                          return (
                                            <span
                                              key={langCode}
                                              className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700"
                                            >
                                              {info.nativeName} ({langCode.toUpperCase()})
                                            </span>
                                          );
                                        })}
                                      </div>

                                      <button
                                        type="button"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          setExpandedPreviewId(isExpanded ? null : f.id);
                                        }}
                                        className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 underline underline-offset-2"
                                      >
                                        {isExpanded ? "Hide PDF Preview" : "Preview PDF Fields"}
                                      </button>
                                    </div>

                                    {isExpanded && (
                                      <div
                                        onClick={(e) => e.stopPropagation()}
                                        className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-2"
                                      >
                                        <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
                                          <span>PDF Document Structure ({meta.formCode})</span>
                                          <span className="font-mono text-[11px] text-slate-500">
                                            Source: {f.sourceLanguage.toUpperCase()}
                                          </span>
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                          {meta.previewSections.map((sec, idx) => (
                                            <div
                                              key={idx}
                                              className="rounded-md border border-slate-200 bg-white p-2"
                                            >
                                              <p className="text-[11px] font-bold text-slate-800">
                                                {idx + 1}. {sec.sectionTitle}
                                              </p>
                                              <div className="mt-1 flex flex-wrap gap-1">
                                                {sec.fields.map((fieldLabel, fIdx) => (
                                                  <span
                                                    key={fIdx}
                                                    className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-700"
                                                  >
                                                    {fieldLabel}
                                                  </span>
                                                ))}
                                              </div>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </>
                    )}
                  </div>

                  {/* 3. Output Language Selection (Interactive Cards instead of raw select) */}
                  {selectedForm && (
                    <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 sm:p-5 shadow-2xs">
                      <div className="flex items-center justify-between">
                        <div>
                          <label htmlFor="output-select" className="block text-xs font-bold uppercase tracking-wider text-slate-800">
                            {t("selectOutputLanguage")}
                          </label>
                          <p className="text-xs text-slate-500 mt-0.5">
                            Choose the language in which the final official PDF form will be completed.
                          </p>
                        </div>
                        <span className="rounded-lg bg-slate-100 px-2.5 py-1 font-mono text-xs font-bold uppercase text-slate-700">
                          PDF: {outputLanguage}
                        </span>
                      </div>

                      <select
                        id="output-select"
                        className="sr-only"
                        value={outputLanguage}
                        onChange={(e) => setOutputLanguage(e.target.value)}
                      >
                        {selectedForm.supportedOutputLanguages.map((lang) => (
                          <option key={lang} value={lang}>
                            {lang}
                          </option>
                        ))}
                      </select>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                        {selectedForm.supportedOutputLanguages.map((lang) => {
                          const info = getLanguageByCode(lang);
                          const isSelected = outputLanguage === lang;
                          return (
                            <button
                              key={lang}
                              type="button"
                              aria-label={`Output language: ${info.nativeName}`}
                              aria-pressed={isSelected}
                              onClick={() => setOutputLanguage(lang)}
                              className={`flex items-center justify-between rounded-xl border p-3 text-start transition-all ${
                                isSelected
                                  ? "border-indigo-600 bg-indigo-50/80 text-indigo-950 ring-2 ring-indigo-600/15"
                                  : "border-slate-200 bg-slate-50/60 text-slate-800 hover:border-indigo-300 hover:bg-white"
                              }`}
                            >
                              <div>
                                <span className="block text-sm font-bold">
                                  {info.nativeName}
                                </span>
                                <span className="block text-xs text-slate-500">
                                  {info.englishName}
                                </span>
                              </div>
                              <span
                                className={`rounded-md px-2 py-0.5 font-mono text-[10px] font-bold uppercase ${
                                  isSelected
                                    ? "bg-indigo-600 text-white"
                                    : "bg-slate-200/80 text-slate-600"
                                }`}
                              >
                                {info.code}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* 4. Privacy Notice */}
                  <div className="space-y-3 rounded-xl border border-indigo-200/80 bg-indigo-50/50 p-4">
                    <div className="flex items-center gap-2 text-indigo-700">
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-950">{t("privacyNoticeTitle")}</h3>
                    </div>
                    <p className="text-xs leading-relaxed text-slate-700">{t("privacyNoticeBody")}</p>
                    <label className="flex items-center gap-3 cursor-pointer select-none text-slate-900 pt-1">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-slate-300 bg-white text-indigo-600 focus:ring-indigo-500/30 cursor-pointer"
                        checked={privacyAccepted}
                        onChange={(e) => setPrivacyAccepted(e.target.checked)}
                      />
                      <span className="text-xs font-semibold">{t("acceptPrivacy")}</span>
                    </label>
                  </div>

                  {/* 5. Submit Button */}
                  <button
                    type="submit"
                    disabled={!privacyAccepted || submitting || forms.length === 0}
                    className="btn-primary w-full py-3.5 text-sm font-semibold"
                  >
                    {submitting ? (
                      <div className="flex items-center justify-center gap-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                        <span>{tc("loading")}</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center gap-2">
                        <span>{t("startSession")}</span>
                        <svg className="h-4 w-4 rtl:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                      </div>
                    )}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
