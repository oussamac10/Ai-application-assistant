"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { getSessionToken, removeSessionToken } from "@/features/form-session/services/sessionCredentials";
import {
  extractExportErrorCode,
  resolveExportError,
} from "@/features/form-session/utils/resolveExportErrorMessage";
import { createExport, downloadExportBlob, getSession, getSummary, ExportResponse, SubmissionChecklistItem, ApiError, TokenMissingError } from "@/features/form-session/services/apiClient";
import { useSafeAuth } from "@/features/auth/hooks/useSafeAuth";
import { claimApplication } from "@/features/applications/services/applicationsClient";
import { ExportAccountGateModal } from "@/features/applications/components/ExportAccountGateModal";
import { Lock, Check, ClipboardCheck, FileDown, Download, Loader2, Landmark, Send, FileText } from "lucide-react";

function formatSubmissionChannelLabel(method: string): string {
  switch (method) {
    case "in_person":
      return "In-Person Appointment";
    case "online":
      return "Online Portal Upload";
    case "postal_mail":
      return "Postal Mail";
    case "print_and_sign":
      return "Print & Sign";
    default:
      return method.replace(/_/g, " ");
  }
}

type ExportState = "ready" | "creating_export" | "export_ready" | "downloading" | "download_failed" | "export_expired" | "token_missing";

export default function SessionComplete() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const t = useTranslations("complete");
  const tc = useTranslations("common");
  const ts = useTranslations("signature");

  const auth = useSafeAuth();
  const [isExportGateOpen, setIsExportGateOpen] = useState<boolean>(false);
  const [exportState, setExportState] = useState<ExportState>("ready");
  const [exportData, setExportData] = useState<ExportResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [exportSupported, setExportSupported] = useState<boolean | null>(null);
  const [needsHandwrittenSignature, setNeedsHandwrittenSignature] =
    useState<boolean>(false);
  const [checklistItems, setChecklistItems] = useState<
    SubmissionChecklistItem[]
  >([]);
  const [checkedIds, setCheckedIds] = useState<Record<string, boolean>>({});
  const [canResign, setCanResign] = useState<boolean>(false);
  const [canRetry, setCanRetry] = useState<boolean>(true);
  const [submissionMethod, setSubmissionMethod] = useState<string>("print_and_sign");
  const [submissionInstructions, setSubmissionInstructions] = useState<string | null>(null);
  const [sessionRequiredDocs, setSessionRequiredDocs] = useState<string[]>([]);
  const [isSponsoredCase, setIsSponsoredCase] = useState<boolean>(false);
  const [organizationName, setOrganizationName] = useState<string | null>(null);

  // Auto-claim session when authenticated user visits complete page with an anonymous session token
  useEffect(() => {
    if (auth?.user && sessionId) {
      const token = getSessionToken(sessionId);
      if (token) {
        claimApplication(sessionId, token)
          .then(() => removeSessionToken(sessionId))
          .catch(() => {});
      }
    }
  }, [auth?.user, sessionId]);

  useEffect(() => {
    let cancelled = false;
    async function loadSession() {
      try {
        const session = await getSession(sessionId);
        if (!cancelled) {
          setExportSupported(session.exportSupported ?? true);
          if (session.submissionMethod) {
            setSubmissionMethod(session.submissionMethod);
          }
          setSubmissionInstructions(session.instructions ?? null);
          setSessionRequiredDocs(session.requiredDocuments ?? []);
          setIsSponsoredCase(Boolean(session.isSponsoredCase));
          setOrganizationName(session.organizationName ?? null);
        }
        try {
          const summary = await getSummary(sessionId);
          if (!cancelled) {
            setNeedsHandwrittenSignature(
              summary.fields.some(
                (f) => f.answerState === "pending_manual_signature",
              ),
            );
            if (summary.submissionChecklist) {
              setChecklistItems(summary.submissionChecklist);
            }
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

  const toggleChecklistItem = (id: string) => {
    setCheckedIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleStartNew = () => {
    removeSessionToken(sessionId);
    router.push("/application");
  };

  const handleGeneratePdf = async () => {
    if (!auth?.user && !isSponsoredCase) {
      setIsExportGateOpen(true);
      return;
    }
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
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center bg-[#0A0E17] px-4 py-10 text-slate-100">
      <div className="w-full max-w-2xl">
        <div className="surface-panel rounded-2xl p-8 sm:p-10 text-center">
          <div className="flex flex-col items-center">
            {/* Celebratory Animated Emerald Verification Seal (Spring Scale-In + Aura Pulse Ring) */}
            <div className="relative mb-6 flex items-center justify-center">
              <div className="absolute h-20 w-20 rounded-full bg-emerald-500/20 animate-ping motion-reduce:animate-none opacity-40 pointer-events-none" />
              <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border-2 border-emerald-500/50 bg-emerald-500/10 text-emerald-400 shadow-[0_0_30px_rgb(var(--brand-500-rgb)/0.35)] animate-in zoom-in-50 duration-500 ease-out motion-reduce:animate-none">
                <Check className="h-8 w-8 text-emerald-400 animate-in zoom-in-75 duration-700 ease-out motion-reduce:animate-none" strokeWidth={2.5} />
              </div>
            </div>

            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-mono font-bold text-emerald-400 mb-2 uppercase tracking-wider">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse motion-reduce:animate-none" />
              <span className="tabular-nums">Step 4 of 4 • Complete & Verified</span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              {t("title")}
            </h1>
            <p className="mt-1.5 text-sm text-slate-400">
              {t("subtitle")}
            </p>

            {/* Structured PDF Receipt Card */}
            <div className="mt-6 w-full rounded-2xl border border-white/10 bg-[#0A0E17] p-5 text-start space-y-3.5 shadow-sm">
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  <span className="text-xs font-semibold text-slate-200">
                    Your Completed Form
                  </span>
                </div>
                <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 rounded-md">
                  Official PDF
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div>
                  <span className="text-[11px] font-medium text-slate-500 block">Status</span>
                  <span className="text-white font-semibold block mt-0.5">Ready to Download</span>
                </div>
                <div>
                  <span className="text-[11px] font-medium text-slate-500 block">Format</span>
                  <span className="text-white font-semibold text-xs block mt-0.5">Print & Submit PDF</span>
                </div>
                <div className="col-span-2 sm:col-span-1">
                  <span className="text-[11px] font-medium text-slate-500 block">Privacy</span>
                  <span className="text-emerald-400 font-semibold text-xs flex items-center gap-1 mt-0.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    Private & Encrypted
                  </span>
                </div>
              </div>
            </div>

            {needsHandwrittenSignature && (
              <div
                role="status"
                data-testid="handwritten-signature-reminder"
                className="mt-5 w-full rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-start text-sm leading-relaxed text-amber-200"
              >
                <p className="font-bold">{ts("reminderTitle")}</p>
                <p className="mt-1">{ts("printReminder")}</p>
              </div>
            )}

            {checklistItems.length > 0 && (
              <div
                data-testid="submission-checklist"
                className="mt-5 w-full rounded-2xl border border-white/10 bg-[#0A0E17] p-5 text-start space-y-3.5 shadow-sm"
              >
                <div className="space-y-0.5">
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    <ClipboardCheck className="h-4 w-4 text-emerald-400 shrink-0" />
                    <span>{t("checklistTitle")}</span>
                  </h2>
                  <p className="text-xs text-slate-400">
                    {t("checklistSubtitle")}
                  </p>
                </div>

                <ul className="space-y-2.5 pt-1">
                  {checklistItems.map((item) => {
                    const isChecked = Boolean(checkedIds[item.id]);
                    return (
                      <li key={item.id}>
                        <label
                          className={`flex items-start gap-3 rounded-xl border p-3.5 cursor-pointer transition-all duration-200 ${
                            isChecked
                              ? "border-emerald-500 bg-emerald-500/15 shadow-[0_0_12px_rgb(var(--brand-500-rgb)/0.15)] ring-2 ring-emerald-500/20 scale-[1.005]"
                              : "border-white/10 bg-[#0F1522] hover:bg-[#151D2E] hover:border-white/20"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleChecklistItem(item.id)}
                            className="mt-0.5 h-4 w-4 rounded border-white/20 bg-[#0A0E17] text-emerald-500 focus:ring-emerald-500/30 accent-emerald-500 shrink-0 transition-transform active:scale-90 cursor-pointer"
                          />
                          <div className="space-y-0.5 text-xs transition-opacity duration-200">
                            <span
                              className={`font-semibold block transition-colors duration-200 ${
                                isChecked
                                  ? "line-through text-emerald-300/80"
                                  : "text-white"
                              }`}
                            >
                              {item.title}
                            </span>
                            <span
                              className={`leading-relaxed block transition-colors duration-200 ${
                                isChecked ? "text-emerald-400/70 line-through decoration-emerald-400/50" : "text-slate-400"
                              }`}
                            >
                              {item.description}
                            </span>
                          </div>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            {(submissionInstructions || sessionRequiredDocs.length > 0) && (
              <div
                data-testid="submission-instructions-card"
                className="mt-5 w-full rounded-2xl border border-emerald-500/30 bg-[#0A0E17] p-5 text-start space-y-3.5 shadow-sm"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <Send className="h-4 w-4 text-emerald-400 shrink-0" />
                    <h2 className="text-sm font-bold text-white">
                      Official Submission Instructions
                    </h2>
                  </div>
                  <span className="inline-flex items-center rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-emerald-400">
                    {formatSubmissionChannelLabel(submissionMethod)}
                  </span>
                </div>

                {organizationName && (
                  <div className="flex items-center gap-2 text-xs text-slate-300">
                    <Landmark className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                    <span>
                      Sponsored intake prepared with{" "}
                      <strong className="text-white">{organizationName}</strong>
                    </span>
                  </div>
                )}

                {submissionInstructions && (
                  <p className="text-xs leading-relaxed text-slate-300">
                    {submissionInstructions}
                  </p>
                )}

                {sessionRequiredDocs.length > 0 && (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
                      <FileText className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                      <span>Supporting Documents to Attach</span>
                    </div>
                    <ul className="space-y-1.5 text-xs text-slate-300">
                      {sessionRequiredDocs.map((docName, idx) => (
                        <li key={`${idx}-${docName}`} className="flex items-start gap-2">
                          <Check className="h-3.5 w-3.5 text-emerald-400 mt-0.5 shrink-0" />
                          <span>{docName}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            <div className="my-6 w-full border-t border-white/10" />

            <p className="text-sm leading-relaxed text-slate-300">
              {t("body")}
            </p>

            {exportSupported === false && (
              <div className="mt-4 w-full rounded-xl border border-white/10 bg-[#0A0E17] p-4 text-xs text-slate-300">
                {t("dynamicExportUnsupported")}
              </div>
            )}

            {errorMsg && (
              <div
                role="alert"
                className="mt-4 w-full rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-200"
              >
                {errorMsg}
              </div>
            )}

            {/* Interactive Actions */}
            <div className="mt-7 w-full space-y-3">
              {!auth?.user && !isSponsoredCase && exportSupported === true && exportState === "ready" && (
                <div className="flex items-center gap-2.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-slate-200 text-start">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-emerald-500 text-slate-950">
                    <Lock className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <span className="font-semibold text-white block">{t("exportAccountRequiredTitle")}</span>
                    <span className="text-slate-300">{t("exportAccountRequiredNotice")}</span>
                  </div>
                </div>
              )}

              {exportSupported === true && exportState === "ready" && (
                <button
                  onClick={handleGeneratePdf}
                  className="btn-primary w-full py-3.5 text-sm font-bold active:scale-[0.98] transition-all"
                >
                  <FileDown className="h-4 w-4" />
                  <span>{t("generatePdf")}</span>
                </button>
              )}

              {exportState === "creating_export" && (
                <button
                  disabled
                  className="btn-secondary w-full py-3.5 text-sm font-medium cursor-not-allowed"
                >
                  <Loader2 className="h-4 w-4 animate-spin text-emerald-400" />
                  <span>{t("preparingPdf")}</span>
                </button>
              )}

              {exportState === "export_ready" && (
                <div className="space-y-3">
                  <div className="text-xs text-emerald-400 font-semibold flex items-center justify-center gap-1.5 animate-in fade-in duration-300 motion-reduce:animate-none">
                    <Check className="h-4 w-4" strokeWidth={2.5} />
                    <span>{t("pdfReady")}</span>
                  </div>
                  <button
                    onClick={handleDownloadPdf}
                    className="btn-primary w-full py-3.5 text-sm font-bold active:scale-[0.98]"
                  >
                    <Download className="h-4 w-4" />
                    <span>{t("downloadPdf")}</span>
                  </button>
                </div>
              )}

              {exportState === "downloading" && (
                <button
                  disabled
                  className="btn-secondary w-full py-3.5 text-sm font-medium cursor-not-allowed"
                >
                  <Loader2 className="h-4 w-4 animate-spin text-emerald-400" />
                  <span>{tc("loading")}</span>
                </button>
              )}

              {(exportState === "export_expired" ||
                (exportState === "download_failed" && canRetry)) && (
                <button
                  data-testid="retry-export"
                  onClick={handleGeneratePdf}
                  className="btn-primary w-full py-3.5 text-sm font-semibold active:scale-[0.98] transition-all"
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

      <ExportAccountGateModal
        isOpen={isExportGateOpen}
        onClose={() => setIsExportGateOpen(false)}
        sessionId={sessionId}
      />
    </main>
  );
}
