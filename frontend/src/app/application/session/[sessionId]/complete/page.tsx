"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { removeSessionToken } from "@/features/form-session/services/sessionCredentials";
import {
  extractExportErrorCode,
  resolveExportError,
} from "@/features/form-session/utils/resolveExportErrorMessage";
import { createExport, downloadExportBlob, getSession, getSummary, ExportResponse, ApiError, TokenMissingError } from "@/features/form-session/services/apiClient";

type ExportState = "ready" | "creating_export" | "export_ready" | "downloading" | "download_failed" | "export_expired" | "token_missing";

export default function SessionComplete() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const t = useTranslations("complete");
  const tc = useTranslations("common");
  const ts = useTranslations("signature");

  const [exportState, setExportState] = useState<ExportState>("ready");
  const [exportData, setExportData] = useState<ExportResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [exportSupported, setExportSupported] = useState<boolean | null>(null);
  const [needsHandwrittenSignature, setNeedsHandwrittenSignature] =
    useState<boolean>(false);
  const [canResign, setCanResign] = useState<boolean>(false);
  const [canRetry, setCanRetry] = useState<boolean>(true);

  useEffect(() => {
    let cancelled = false;
    async function loadSession() {
      try {
        const session = await getSession(sessionId);
        if (!cancelled) {
          setExportSupported(session.exportSupported ?? true);
        }
        try {
          const summary = await getSummary(sessionId);
          if (!cancelled) {
            setNeedsHandwrittenSignature(
              summary.fields.some(
                (f) => f.answerState === "pending_manual_signature",
              ),
            );
          }
        } catch {
          // ignore
        }
      } catch {
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
        setExportState("token_missing");
        setErrorMsg("Your session credentials were lost (the tab may have been closed or refreshed). Redirecting you to start a new session…");
        setTimeout(() => router.push("/application"), 3000);
        return;
      }
      setExportState("download_failed");

      const presented = resolveExportError(t, error);
      setCanResign(presented.canResign);
      setCanRetry(presented.canRetry);

      if (error instanceof ApiError && extractExportErrorCode(error) === null) {
        if (error.status === 401 || error.status === 403) {
          setErrorMsg(t("error_export_forbidden"));
          setCanRetry(false);
          setCanResign(false);
          return;
        }
        if (error.status === 422) {
          setErrorMsg(t("overflowError"));
          return;
        }
      }
      setErrorMsg(presented.message);
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
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-4 py-10 text-slate-900">
      <div className="w-full max-w-2xl">
        <div className="surface-panel rounded-2xl p-8 sm:p-10 text-center">
          <div className="flex flex-col items-center">
            {/* Green Success Checkmark Badge */}
            <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-200 bg-emerald-50 text-emerald-600">
              <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 mb-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
              <span className="tabular-nums">Step 4 of 4 • Complete</span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
              {t("title")}
            </h1>
            <p className="mt-1.5 text-sm text-slate-600">
              {t("subtitle")}
            </p>

            {/* Document Certificate Metadata Box */}
            <div className="mt-6 w-full rounded-xl border border-slate-200 bg-slate-50/70 p-5 text-start space-y-3">
              <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
                  Document Package
                </span>
                <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 border border-indigo-200 px-2.5 py-0.5 text-[11px] font-semibold text-indigo-700">
                  Official AcroForm
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 block">Session Reference</span>
                  <span className="font-mono text-slate-800 font-semibold truncate block mt-0.5 tabular-nums">{sessionId.slice(0, 8)}…</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Compilation</span>
                  <span className="font-semibold text-slate-800 block mt-0.5">Deterministic Fill</span>
                </div>
                <div className="col-span-2 sm:col-span-1">
                  <span className="text-slate-500 block">Data Retention</span>
                  <span className="font-semibold text-emerald-700 block mt-0.5">Zero-Retention</span>
                </div>
              </div>
            </div>

            {needsHandwrittenSignature && (
              <div
                role="status"
                data-testid="handwritten-signature-reminder"
                className="mt-5 w-full rounded-xl border border-amber-200 bg-amber-50 p-4 text-start text-sm leading-relaxed text-amber-900"
              >
                <p className="font-bold">{ts("reminderTitle")}</p>
                <p className="mt-1">{ts("printReminder")}</p>
              </div>
            )}

            <div className="my-6 w-full border-t border-slate-200" />

            <p className="text-sm leading-relaxed text-slate-700">
              {t("body")}
            </p>

            {exportSupported === false && (
              <div className="mt-4 w-full rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700">
                {t("dynamicExportUnsupported")}
              </div>
            )}

            {errorMsg && (
              <div
                role="alert"
                className="mt-4 w-full rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800"
              >
                {errorMsg}
              </div>
            )}

            {/* Interactive Actions */}
            <div className="mt-7 w-full space-y-3">
              {exportSupported === true && exportState === "ready" && (
                <button
                  onClick={handleGeneratePdf}
                  className="btn-primary w-full py-3.5 text-sm font-semibold"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>{t("generatePdf")}</span>
                </button>
              )}

              {exportState === "creating_export" && (
                <button
                  disabled
                  className="btn-secondary w-full py-3.5 text-sm font-medium cursor-not-allowed"
                >
                  <svg className="h-4 w-4 animate-spin text-indigo-600" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span>{t("preparingPdf")}</span>
                </button>
              )}

              {exportState === "export_ready" && (
                <div className="space-y-3">
                  <div className="text-xs text-emerald-700 font-semibold flex items-center justify-center gap-1.5">
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                    <span>{t("pdfReady")}</span>
                  </div>
                  <button
                    onClick={handleDownloadPdf}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-600 bg-emerald-600 py-3.5 text-sm font-semibold text-white shadow-xs transition-colors hover:bg-emerald-700"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    <span>{t("downloadPdf")}</span>
                  </button>
                </div>
              )}

              {exportState === "downloading" && (
                <button
                  disabled
                  className="btn-secondary w-full py-3.5 text-sm font-medium cursor-not-allowed"
                >
                  <svg className="h-4 w-4 animate-spin text-emerald-600" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span>{tc("loading")}</span>
                </button>
              )}

              {(exportState === "export_expired" ||
                (exportState === "download_failed" && canRetry)) && (
                <button
                  data-testid="retry-export"
                  onClick={handleGeneratePdf}
                  className="btn-primary w-full py-3.5 text-sm font-semibold"
                >
                  {t("regeneratePdf")}
                </button>
              )}

              {exportState === "download_failed" && canResign && (
                <button
                  data-testid="return-to-signature"
                  onClick={() => router.push(`/application/session/${sessionId}`)}
                  className="btn-secondary w-full py-3.5 text-sm font-medium"
                >
                  {t("returnToSignature")}
                </button>
              )}

              <button
                onClick={handleStartNew}
                className="btn-secondary w-full py-3.5 text-sm font-medium"
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
