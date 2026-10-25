"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { checkBackendHealth, checkDatabaseHealth } from "@/services/api";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";

type ConnectionStatus = "loading" | "connected" | "unavailable";

export default function Home() {
  const [status, setStatus] = useState<ConnectionStatus>("loading");
  const [dbStatus, setDbStatus] = useState<string>("checking");

  useEffect(() => {
    let active = true;

    async function verifyConnections() {
      const isBackendAlive = await checkBackendHealth();

      if (!active) return;

      if (isBackendAlive) {
        setStatus("connected");
        try {
          const databaseHealth = await checkDatabaseHealth();
          if (active) {
            setDbStatus(databaseHealth.database);
          }
        } catch {
          if (active) {
            setDbStatus("unavailable");
          }
        }
      } else {
        setStatus("unavailable");
        setDbStatus("unavailable");
      }
    }

    verifyConnections();

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="min-h-[calc(100vh-3.5rem)] px-4 py-12 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        {/* Hero Section */}
        <div className="flex flex-col items-center text-center pt-4 sm:pt-8">
          {/* Top Pill / Badge */}
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3.5 py-1 text-xs font-semibold text-indigo-700">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
            <span>Phase 1 Monorepo Foundation</span>
            <span className="text-indigo-300">•</span>
            <span className="text-slate-700">{UNIVERSAL_LANGUAGES.length}+ Universal Languages</span>
          </div>

          {/* Main Title */}
          <h1 className="mt-6 max-w-4xl text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl lg:text-6xl sm:leading-[1.1]">
            <span className="block">AI Form Assistant</span>
            <span className="mt-2 block text-2xl sm:text-4xl font-semibold text-indigo-700 tracking-tight">
              Complete Official Forms Across Any Language
            </span>
          </h1>

          {/* Description */}
          <p className="mt-5 max-w-2xl text-base text-slate-600 leading-relaxed">
            Eliminate language barriers in administrative and civic paperwork. Answer one question at a time in{" "}
            <strong className="font-semibold text-slate-900">{UNIVERSAL_LANGUAGES.length}+ world languages</strong>{" "}
            (Arabic, French, German, English, Spanish, Turkish, Ukrainian, Persian, Urdu, and more). Every answer is preserved,
            normalized to canonical ISO standards, and verified by you before export.
          </p>

          {/* Universal Language Pills Strip (No Flags) */}
          <div className="mt-5 flex flex-wrap items-center justify-center gap-1.5 max-w-3xl">
            {UNIVERSAL_LANGUAGES.slice(0, 12).map((lang) => (
              <span
                key={lang.code}
                className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-2xs"
              >
                <span className="font-mono text-[10px] font-bold uppercase text-indigo-600">
                  {lang.code}
                </span>
                <span>{lang.nativeName}</span>
              </span>
            ))}
            <span className="inline-flex items-center rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">
              +{UNIVERSAL_LANGUAGES.length - 12} more languages
            </span>
          </div>

          {/* Action CTAs */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3 w-full sm:w-auto">
            <Link
              href="/application"
              className="btn-primary w-full sm:w-auto px-7 py-3.5 text-sm font-semibold"
            >
              <span>Start Guided Application</span>
              <svg
                className="h-4 w-4 rtl:rotate-180"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </Link>

            <Link
              href="/application"
              className="btn-secondary w-full sm:w-auto px-6 py-3.5 text-sm font-medium"
            >
              <svg
                className="h-4 w-4 text-indigo-600"
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
              <span>Upload Any PDF Form</span>
            </Link>
          </div>
        </div>

        {/* Architectural Principles Grid */}
        <div className="mt-16 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="surface-card rounded-2xl p-6">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-200 bg-indigo-50 text-indigo-600">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
              </svg>
            </div>
            <h2 className="text-sm font-bold text-slate-900">Universal 3-Language Engine</h2>
            <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
              Independent source, user, and output languages with full LTR and RTL layout support across 36+ languages.
            </p>
          </div>

          <div className="surface-card rounded-2xl p-6">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-200 bg-indigo-50 text-indigo-600">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h2 className="text-sm font-bold text-slate-900">Deterministic Validation</h2>
            <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
              Canonical ISO dates, currencies, and choices validated deterministically without invented data.
            </p>
          </div>

          <div className="surface-card rounded-2xl p-6">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-200 bg-indigo-50 text-indigo-600">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h2 className="text-sm font-bold text-slate-900">Privacy by Design</h2>
            <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
              Temporary anonymous sessions with cryptographic ownership tokens and automatic expiration.
            </p>
          </div>

          <div className="surface-card rounded-2xl p-6">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-200 bg-indigo-50 text-indigo-600">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h2 className="text-sm font-bold text-slate-900">Universal PDF Export</h2>
            <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
              Categorized templates with miniature PDF previews, digital signature capture, and mapped PDF output.
            </p>
          </div>
        </div>

        {/* System Telemetry & Health Section (Maintains test compatibility) */}
        <div className="mt-12 surface-panel rounded-2xl p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
            <div>
              <h2 className="text-base font-bold text-slate-900">System Status & Environment Health</h2>
              <p className="mt-0.5 text-xs text-slate-500">
                Real-time API and database connectivity verification
              </p>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span>Environment Telemetry</span>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Backend Status Box */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Backend Status
                </p>
                <span className="text-xs font-mono text-slate-500">FastAPI</span>
              </div>
              <div className="mt-2.5 flex items-center gap-2.5">
                {status === "loading" && (
                  <>
                    <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
                    <span className="text-sm font-semibold text-amber-800">
                      Checking backend connection
                    </span>
                  </>
                )}
                {status === "connected" && (
                  <>
                    <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" />
                    <span className="text-sm font-semibold text-emerald-800">
                      Backend connected
                    </span>
                  </>
                )}
                {status === "unavailable" && (
                  <>
                    <span className="h-2.5 w-2.5 rounded-full bg-rose-600" />
                    <span className="text-sm font-semibold text-rose-800">
                      Backend unavailable
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Database Connection Box */}
            <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Database Connection
                </p>
                <span className="text-xs font-mono text-slate-500">PostgreSQL</span>
              </div>
              <div className="mt-2.5 flex items-center gap-2.5">
                {dbStatus === "checking" && (
                  <>
                    <span className="h-2.5 w-2.5 rounded-full bg-slate-400" />
                    <span className="text-sm font-semibold text-slate-700">
                      Checking database...
                    </span>
                  </>
                )}
                {dbStatus === "connected" && (
                  <>
                    <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" />
                    <span className="text-sm font-semibold text-emerald-800">
                      Connected
                    </span>
                  </>
                )}
                {dbStatus === "unavailable" && (
                  <>
                    <span className="h-2.5 w-2.5 rounded-full bg-rose-600" />
                    <span className="text-sm font-semibold text-rose-800">
                      Unavailable
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
