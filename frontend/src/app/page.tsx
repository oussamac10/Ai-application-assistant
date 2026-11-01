"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import {
  UNIVERSAL_LANGUAGES,
  getLanguageByCode,
} from "@/features/form-session/utils/languages";
import {
  PublishedForm,
  createSession,
  getPublishedForms,
} from "@/features/form-session/services/apiClient";
import { setSessionToken } from "@/features/form-session/services/sessionCredentials";

const LAUNCH_UI_CODES = ["en", "de", "fr", "ar", "tr", "uk", "es", "ru"] as const;

export default function Home() {
  const router = useRouter();
  const t = useTranslations("home");
  const tc = useTranslations("common");
  const { locale, setLocale } = useLanguage();

  const [forms, setForms] = useState<PublishedForm[]>([]);
  const [loadingForms, setLoadingForms] = useState<boolean>(true);
  const [launchingId, setLaunchingId] = useState<string | null>(null);
  const [launchError, setLaunchError] = useState<string | null>(null);

  const activeLanguage = useMemo(() => getLanguageByCode(locale), [locale]);
  const launchLanguages = useMemo(
    () => LAUNCH_UI_CODES.map((code) => getLanguageByCode(code)),
    [],
  );

  useEffect(() => {
    let active = true;
    setLoadingForms(true);

    getPublishedForms()
      .then((items) => {
        if (!active) return;
        const getRegionPriority = (key: string) => {
          if (key.startsWith("eu-")) return 1;
          if (key.startsWith("us-")) return 2;
          if (key.startsWith("uk-")) return 3;
          if (key.startsWith("de-")) return 4;
          return 5;
        };
        const sorted = [...items].sort((a, b) => {
          const pA = getRegionPriority(a.templateKey);
          const pB = getRegionPriority(b.templateKey);
          if (pA !== pB) return pA - pB;
          return a.name.localeCompare(b.name);
        });
        setForms(sorted);
      })
      .catch(() => {
        if (active) setForms([]);
      })
      .finally(() => {
        if (active) setLoadingForms(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const handleQuickLaunch = async (form: PublishedForm) => {
    if (launchingId) return;
    setLaunchError(null);
    setLaunchingId(form.id);

    try {
      const outputLang =
        form.supportedOutputLanguages[0] || form.sourceLanguage || "de";
      const session = await createSession(form.id, locale, outputLang);
      if (session.ownershipToken) {
        setSessionToken(session.publicId, session.ownershipToken);
      }
      router.push(`/application/session/${session.publicId}`);
    } catch {
      setLaunchError(t("quickStartError"));
      setLaunchingId(null);
    }
  };

  return (
    <main className="px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-16">
        {/* Hero Section — Grounded in Civic Document Clarity */}
        <section className="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:items-center pt-2">
          <div className="lg:col-span-7 space-y-6 text-start">
            <p className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3.5 py-1 text-xs font-medium text-slate-700 shadow-2xs">
              <span className="h-2 w-2 rounded-full bg-emerald-600" />
              <span>{t("eyebrow")}</span>
            </p>

            <h1 className="max-w-2xl text-3xl font-bold tracking-tight text-slate-900 sm:text-5xl sm:leading-[1.12]">
              {t("headline")}
            </h1>

            <p className="max-w-xl text-base leading-relaxed text-slate-600">
              {t("subheadline")}
            </p>

            {/* Instant 8-Language Switcher Strip (Flag-Free) */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              {launchLanguages.map((lang) => {
                const selected = locale === lang.code;
                return (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => setLocale(lang.code)}
                    aria-pressed={selected}
                    className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                      selected
                        ? "border-indigo-600 bg-indigo-50 text-indigo-950"
                        : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <span className="font-mono text-[10px] uppercase text-indigo-700">
                      {lang.code}
                    </span>
                    <span>{lang.nativeName}</span>
                  </button>
                );
              })}
              <span className="px-2 text-xs text-slate-500">
                <bdi>+{UNIVERSAL_LANGUAGES.length - launchLanguages.length}</bdi>
              </span>
            </div>

            {/* Primary & Secondary Actions */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
              <Link
                href="/application"
                className="btn-primary px-6 py-3.5 text-sm font-semibold"
              >
                <svg
                  className="h-4 w-4 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.75}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
                <span>{t("ctaUpload")}</span>
              </Link>

              <a
                href="#german-forms"
                className="btn-secondary px-5 py-3.5 text-sm font-medium"
              >
                <span>{t("ctaBrowseTemplates")}</span>
              </a>
            </div>
          </div>

          {/* Right Column: Civic Workflow Sheet Preview */}
          <div className="lg:col-span-5">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-5">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3.5">
                <span className="text-xs font-semibold text-slate-900">
                  {t("howItWorksTitle")}
                </span>
                <span
                  className="rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-[11px] font-semibold text-emerald-800"
                  dir="ltr"
                >
                  {activeLanguage.code.toUpperCase()} → OFFICIAL PDF
                </span>
              </div>

              <ol className="space-y-4">
                <li className="space-y-1">
                  <p className="text-sm font-semibold text-slate-900">
                    {t("step1Title")}
                  </p>
                  <p className="text-xs leading-relaxed text-slate-600">
                    {t("step1Body")}
                  </p>
                </li>
                <li className="space-y-1 border-t border-slate-100 pt-3.5">
                  <p className="text-sm font-semibold text-slate-900">
                    {t("step2Title")}
                  </p>
                  <p className="text-xs leading-relaxed text-slate-600">
                    {t("step2Body")}
                  </p>
                </li>
                <li className="space-y-1 border-t border-slate-100 pt-3.5">
                  <p className="text-sm font-semibold text-slate-900">
                    {t("step3Title")}
                  </p>
                  <p className="text-xs leading-relaxed text-slate-600">
                    {t("step3Body")}
                  </p>
                </li>
              </ol>
            </div>
          </div>
        </section>

        {/* Zero-Signup 1-Click Official German Form Register */}
        <section
          id="german-forms"
          className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-2xs"
        >
          <div className="border-b border-slate-200 bg-slate-50/70 px-6 py-5 sm:px-8">
            <h2 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900">
              {t("quickStartTitle")}
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              {t("quickStartSubtitle", { language: activeLanguage.nativeName })}
            </p>
            {launchError && (
              <div
                role="alert"
                className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-800"
              >
                {launchError}
              </div>
            )}
          </div>

          {loadingForms ? (
            <div className="px-6 py-10 text-center text-sm text-slate-500">
              {tc("loading")}
            </div>
          ) : forms.length === 0 ? (
            <div className="px-6 py-8 sm:px-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <p className="text-sm text-slate-600">{t("step1Body")}</p>
              <Link
                href="/application"
                className="btn-primary shrink-0 px-5 py-2.5 text-xs font-semibold"
              >
                {t("ctaUpload")}
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 divide-y divide-slate-200 md:grid-cols-2 md:divide-y-0">
              {forms.slice(0, 16).map((form, index) => {
                const isLaunching = launchingId === form.id;
                const rowBorder =
                  index >= 2 ? "md:border-t md:border-slate-200" : "";
                const colBorder =
                  index % 2 === 1 ? "md:border-s md:border-slate-200" : "";

                const getJurisdictionBadge = (key: string) => {
                  if (key.startsWith("eu-")) return { flag: "🇪🇺", name: "EU / Schengen" };
                  if (key.startsWith("us-")) return { flag: "🇺🇸", name: "United States" };
                  if (key.startsWith("uk-")) return { flag: "🇬🇧", name: "United Kingdom" };
                  if (key.startsWith("de-")) return { flag: "🇩🇪", name: "Germany" };
                  return { flag: "🌐", name: "Official Form" };
                };
                const badge = getJurisdictionBadge(form.templateKey);

                return (
                  <div
                    key={form.id}
                    className={`flex flex-col justify-between gap-4 p-5 sm:px-7 sm:py-5 transition-colors hover:bg-slate-50/70 ${rowBorder} ${colBorder}`}
                  >
                    <div className="space-y-1.5 text-start">
                      <div className="flex items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-1 rounded border border-indigo-200 bg-indigo-50/80 px-2 py-0.5 text-[10px] font-semibold text-indigo-700">
                          <span>{badge.flag}</span>
                          <span>{badge.name}</span>
                        </span>
                        <span
                          className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 font-mono text-[10px] font-semibold uppercase text-slate-600"
                          dir="ltr"
                        >
                          {form.sourceLanguage.toUpperCase()} • PDF
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-slate-900">
                        <bdi>{form.name}</bdi>
                      </h3>
                      {form.description && (
                        <p className="text-xs leading-relaxed text-slate-600 line-clamp-2">
                          <bdi>{form.description}</bdi>
                        </p>
                      )}
                    </div>

                    <div className="flex items-center justify-end pt-1">
                      <button
                        type="button"
                        data-testid={`quick-launch-${form.templateKey}`}
                        disabled={Boolean(launchingId)}
                        onClick={() => handleQuickLaunch(form)}
                        className="inline-flex items-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50/80 px-3.5 py-2 text-xs font-semibold text-indigo-800 transition-colors hover:border-indigo-400 hover:bg-indigo-100 disabled:opacity-60"
                      >
                        <span>
                          {isLaunching
                            ? t("quickStartLaunching")
                            : t("quickStartAction", {
                                language: activeLanguage.nativeName,
                              })}
                        </span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Three Quiet Trust & Regulatory Guardrails */}
        <section className="grid grid-cols-1 gap-6 md:grid-cols-3 border-y border-slate-200 py-10">
          <div className="space-y-1.5 text-start">
            <h2 className="text-sm font-bold text-slate-900">
              {t("trustEuTitle")}
            </h2>
            <p className="text-xs leading-relaxed text-slate-600">
              {t("trustEuBody")}
            </p>
          </div>
          <div className="space-y-1.5 text-start">
            <h2 className="text-sm font-bold text-slate-900">
              {t("trustAccuracyTitle")}
            </h2>
            <p className="text-xs leading-relaxed text-slate-600">
              {t("trustAccuracyBody")}
            </p>
          </div>
          <div className="space-y-1.5 text-start">
            <h2 className="text-sm font-bold text-slate-900">
              {t("trustRdgTitle")}
            </h2>
            <p className="text-xs leading-relaxed text-slate-600">
              {t("trustRdgBody")}
            </p>
          </div>
        </section>

        {/* Transparent Pricing Preview (Transactional Passes First) */}
        <section className="space-y-6 pb-4">
          <div className="max-w-2xl space-y-1.5 text-start">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              {t("pricingTitle")}
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed">
              {t("pricingSubtitle")}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            {/* Free Preview */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 flex flex-col justify-between gap-5">
              <div className="space-y-3 text-start">
                <h3 className="text-sm font-bold text-slate-900">
                  {t("planFreeName")}
                </h3>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-slate-900 tabular-nums">
                    <bdi>{t("planFreePrice")}</bdi>
                  </span>
                  <span className="text-xs text-slate-500">
                    {t("planFreeUnit")}
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-slate-600">
                  {t("planFreeDesc")}
                </p>
              </div>
              <Link
                href="/application"
                className="btn-secondary w-full py-2.5 text-xs font-semibold"
              >
                {t("ctaUpload")}
              </Link>
            </div>

            {/* Single Document Pass */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 flex flex-col justify-between gap-5">
              <div className="space-y-3 text-start">
                <h3 className="text-sm font-bold text-slate-900">
                  {t("planSingleName")}
                </h3>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-slate-900 tabular-nums">
                    <bdi>{t("planSinglePrice")}</bdi>
                  </span>
                  <span className="text-xs text-slate-500">
                    {t("planSingleUnit")}
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-slate-600">
                  {t("planSingleDesc")}
                </p>
              </div>
              <Link
                href="/application"
                className="btn-secondary w-full py-2.5 text-xs font-semibold"
              >
                {t("ctaUpload")}
              </Link>
            </div>

            {/* 5-Document Relocation Pack */}
            <div className="rounded-2xl border-2 border-indigo-600 bg-white p-6 flex flex-col justify-between gap-5 shadow-xs">
              <div className="space-y-3 text-start">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-bold text-slate-900">
                    {t("planPackName")}
                  </h3>
                  <span className="rounded-full bg-indigo-50 border border-indigo-200 px-2.5 py-0.5 text-[11px] font-semibold text-indigo-800">
                    {t("planPackBadge")}
                  </span>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-slate-900 tabular-nums">
                    <bdi>{t("planPackPrice")}</bdi>
                  </span>
                  <span className="text-xs text-slate-500">
                    {t("planPackUnit")}
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-slate-600">
                  {t("planPackDesc")}
                </p>
              </div>
              <Link
                href="/application"
                className="btn-primary w-full py-2.5 text-xs font-semibold"
              >
                {t("ctaUpload")}
              </Link>
            </div>
          </div>

          <p className="text-xs text-slate-500 text-start">
            {t("planAgencyNote")}
          </p>
        </section>
      </div>
    </main>
  );
}
