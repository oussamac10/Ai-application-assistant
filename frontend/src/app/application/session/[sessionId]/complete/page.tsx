"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { removeSessionToken } from "@/features/form-session/services/sessionCredentials";
import { createExport, downloadExportBlob, getSession, ExportResponse, ApiError, TokenMissingError } from "@/features/form-session/services/apiClient";

type ExportState = "ready" | "creating_export" | "export_ready" | "downloading" | "download_failed" | "export_expired" | "token_missing";

export default function SessionComplete() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const t = useTranslations("complete");
  const tc = useTranslations("common");

  const [exportState, setExportState] = useState<ExportState>("ready");
  const [exportData, setExportData] = useState<ExportResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [exportSupported, setExportSupported] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadSession() {
      try {
        const session = await getSession(sessionId);
        if (!cancelled) {
          setExportSupported(session.exportSupported ?? true);
        }
      } catch {
        // If we can't determine origin, default to allowing the normal
        // export flow rather than silently hiding it.
        if (!cancelled) setExportSupported(true);
      }
    }
    loadSession();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const handleStartNew = () => {
    removeSessionToken(sessionId);
    router.push("/application");
  };

  const handleGeneratePdf = async () => {
    setExportState("creating_export");
    setErrorMsg(null);
    try {
      const data = await createExport(sessionId);
      setExportData(data);
      setExportState("export_ready");
    } catch (error: any) {
      console.error("PDF generation failed:", error);
      if (error instanceof TokenMissingError) {
        // Session token was lost (tab closed / storage cleared) — redirect to start fresh
        setExportState("token_missing");
        setErrorMsg("Your session credentials were lost (the tab may have been closed or refreshed). Redirecting you to start a new session…");
        setTimeout(() => router.push("/application"), 3000);
        return;
      }
      setExportState("download_failed");
      if (error instanceof ApiError) {
        if (error.status === 401 || error.status === 403) {
          setExportState("token_missing");
          setErrorMsg("Your session credentials are no longer valid. Redirecting you to start a new session…");
          setTimeout(() => router.push("/application"), 3000);
        } else if (error.status === 422) {
          setErrorMsg(t("overflowError"));
        } else {
          setErrorMsg(error.detail || t("exportFailed"));
        }
      } else {
        setErrorMsg(t("exportFailed"));
      }
    }
  };

  const handleDownloadPdf = async () => {
    if (!exportData) return;
    setExportState("downloading");
    setErrorMsg(null);
    try {
      const blob = await downloadExportBlob(sessionId, exportData.downloadUrl);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = exportData.fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      setExportState("export_ready");
    } catch (error: any) {
      console.error("PDF download failed:", error);
      setExportState("download_failed");
      if (error instanceof ApiError) {
        if (error.status === 422 && error.detail?.includes("expired")) {
          setExportState("export_expired");
          setErrorMsg(t("exportExpired"));
        } else {
          setErrorMsg(error.detail || t("exportFailed"));
        }
      } else {
        setErrorMsg(t("exportFailed"));
      }
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 px-4 text-slate-100">
      <div className="w-full max-w-md">
        <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/60 p-8 text-center shadow-2xl backdrop-blur-xl animate-fade-in">
          {/* Glowing decorator background */}
          <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-emerald-500/10 blur-3xl" />

          <div className="relative z-10 flex flex-col items-center">
            {/* Green Success Checkmark */}
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-500 shadow-lg shadow-emerald-500/30">
              <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <h1 className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent">
              {t("title")}
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              {t("subtitle")}
            </p>

            <div className="my-6 w-full border-t border-slate-800" />

            <p className="text-sm leading-relaxed text-slate-300">
              {t("body")}
            </p>

            {exportSupported === false && (
              <div className="mt-4 w-full rounded-xl border border-slate-800 bg-slate-950/40 p-3 text-xs text-slate-300">
                {t("dynamicExportUnsupported")}
              </div>
            )}

            {/* Error Message rendering */}
            {errorMsg && (
              <div className="mt-4 w-full rounded-xl border border-rose-900/30 bg-rose-950/20 p-3 text-xs text-rose-300">
                {errorMsg}
              </div>
            )}

            {/* Interactive Actions */}
            <div className="mt-6 w-full space-y-3">
              {exportSupported === true && exportState === "ready" && (
                <button
                  onClick={handleGeneratePdf}
                  className="w-full rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 py-4 text-base font-bold text-white shadow-lg shadow-indigo-500/20 transition hover:opacity-95 active:scale-[0.99]"
                >
                  {t("generatePdf")}
                </button>
              )}

              {exportState === "creating_export" && (
                <button
                  disabled
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-800 py-4 text-base font-bold text-slate-400 cursor-not-allowed"
                >
                  <svg className="h-5 w-5 animate-spin text-indigo-400" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {t("preparingPdf")}
                </button>
              )}

              {exportState === "export_ready" && (
                <div className="space-y-3">
                  <div className="text-xs text-emerald-400 font-medium">✓ {t("pdfReady")}</div>
                  <button
                    onClick={handleDownloadPdf}
                    className="w-full rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 py-4 text-base font-bold text-white shadow-lg shadow-emerald-500/20 transition hover:opacity-95 active:scale-[0.99]"
                  >
                    {t("downloadPdf")}
                  </button>
                </div>
              )}

              {exportState === "downloading" && (
                <button
                  disabled
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-800 py-4 text-base font-bold text-slate-400 cursor-not-allowed"
                >
                  <svg className="h-5 w-5 animate-spin text-emerald-400" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {tc("loading")}
                </button>
              )}

              {(exportState === "download_failed" || exportState === "export_expired") && (
                <button
                  onClick={handleGeneratePdf}
                  className="w-full rounded-xl bg-slate-800 py-4 text-base font-bold text-slate-200 hover:bg-slate-700 transition active:scale-[0.99]"
                >
                  {t("regeneratePdf")}
                </button>
              )}

              <button
                onClick={handleStartNew}
                className="w-full rounded-xl border border-slate-800 bg-slate-950/40 py-4 text-base font-bold text-slate-400 hover:text-slate-200 transition"
              >
                {t("startNew")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
