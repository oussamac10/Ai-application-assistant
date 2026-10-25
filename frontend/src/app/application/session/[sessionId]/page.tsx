"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  startSession,
  getCurrentField,
  fetchSessionPagePreviewBlob,
  skipField,
  submitSignature,
  signAfterPrinting,
  submitAnswer,
  submitClarification,
  confirmAnswer,
  previousField,
  changeAnswer,
  CurrentField,
  AnswerResponse,
} from "@/features/form-session/services/apiClient";
import { removeSessionToken } from "@/features/form-session/services/sessionCredentials";
import {
  canSkipQuestion,
  resolveRequiredness,
} from "@/features/form-session/utils/questionRules";
import {
  parseRowKey,
  rowHeading,
  rowProgressFor,
} from "@/features/form-session/utils/repeatedRows";
import { FieldRenderer } from "@/features/form-session/components/FieldRenderer";
import {
  SignaturePad,
  SignatureValue,
} from "@/features/form-session/components/SignaturePad";
import {
  formatOriginalAnswer,
  formatProposedValue,
} from "@/features/form-session/utils/formatProposedValue";
import ClaimBanner from "@/features/applications/components/ClaimBanner";

type FlowStep =
  | "loading"
  | "error"
  | "answering"
  | "needs_clarification"
  | "awaiting_confirmation"
  | "submitting";

export default function GuidedSession() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const t = useTranslations("workflow");
  const tc = useTranslations("common");
  const te = useTranslations("errors");

  const [step, setStep] = useState<FlowStep>("loading");
  const [currentField, setCurrentFieldData] = useState<CurrentField | null>(
    null,
  );
  const [inputValue, setInputValue] = useState<string>("");
  const [lastAnswer, setLastAnswer] = useState<AnswerResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [errorIsFieldLevel, setErrorIsFieldLevel] = useState<boolean>(false);
  const [allFieldKeys, setAllFieldKeys] = useState<string[]>([]);
  const [clarifyValues, setClarifyValues] = useState<Record<string, any>>({});
  const [showExplanation, setShowExplanation] = useState<boolean>(false);
  const [pagePreviewUrls, setPagePreviewUrls] = useState<Record<number, string>>({});
  const [zoomedPreviewOpen, setZoomedPreviewOpen] = useState<boolean>(false);
  const pagePreviewUrlsRef = useRef<Record<number, string>>({});

  useEffect(() => {
    const activePage = currentField?.pageNumber ?? 1;
    if (!currentField?.sourceDocumentFilename) return;
    if (pagePreviewUrlsRef.current[activePage]) return;

    let cancelled = false;
    fetchSessionPagePreviewBlob(sessionId, activePage)
      .then((blob) => {
        if (cancelled) return;
        const objectUrl = URL.createObjectURL(blob);
        pagePreviewUrlsRef.current[activePage] = objectUrl;
        setPagePreviewUrls((prev) => ({ ...prev, [activePage]: objectUrl }));
      })
      .catch(() => {
        // Fallback schematic mini-map stays visible if preview is unavailable
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, currentField?.pageNumber, currentField?.sourceDocumentFilename]);

  useEffect(() => {
    const urlsRef = pagePreviewUrlsRef;
    return () => {
      Object.values(urlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);

  const initializedSessionRef = useRef<string | null>(null);

  const fetchNextQuestion = useCallback(async () => {
    try {
      setErrorMsg(null);
      setShowExplanation(false);
      const field = await getCurrentField(sessionId);
      console.log(
        "FETCHED FIELD:",
        field.label,
        "KEY:",
        field.key,
        "STATUS:",
        field.currentAnswerStatus,
      );
      setCurrentFieldData(field);

      const total =
        field.progress?.totalQuestions ??
        field.progress?.totalRequiredFields ??
        0;
      const completed =
        field.progress?.answeredQuestions ??
        field.progress?.confirmedRequiredFields ??
        0;
      if (total > 0 && completed >= total) {
        router.push(`/application/session/${sessionId}/summary`);
        return;
      }

      if (field.allFieldKeys) {
        setAllFieldKeys(field.allFieldKeys);
      }
      setInputValue(
        field.currentAnswerStatus ? field.originalAnswer || "" : "",
      );
      if (
        field.fieldType === "signature" &&
        field.currentAnswerStatus &&
        field.normalizedValue &&
        typeof field.normalizedValue === "object" &&
        Array.isArray((field.normalizedValue as any).strokes)
      ) {
        setSignatureValue(field.normalizedValue as SignatureValue);
      } else {
        setSignatureValue(null);
      }

      setStep("answering");
    } catch (err: any) {
      console.error("FETCH NEXT QUESTION ERROR:", err.message, err.detail);
      setErrorMsg(te(err.message) || "Failed to retrieve next form question.");
      setStep("error");
    }
  }, [sessionId, router, te]);

  useEffect(() => {
    if (initializedSessionRef.current === sessionId) return;
    initializedSessionRef.current = sessionId;

    async function initSession() {
      try {
        setStep("loading");
        setErrorMsg(null);

        try {
          await startSession(sessionId);
        } catch (err: any) {
          if (err.status !== 409) throw err;
        }

        await fetchNextQuestion();
      } catch (err: any) {
        setErrorMsg(
          te(err.message) ||
            "Failed to initialize assisted session. Please retry.",
        );
        setStep("error");
      }
    }

    initSession();
  }, [sessionId, te, fetchNextQuestion]);

  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentField || !inputValue.trim() || step === "submitting") return;

    try {
      setStep("submitting");
      setErrorMsg(null);
      setErrorIsFieldLevel(false);

      console.log(
        "SUBMITTING ANSWER FOR FIELD:",
        currentField.fieldId,
        "VALUE:",
        inputValue,
      );
      const response = await submitAnswer(
        sessionId,
        currentField.fieldId,
        inputValue,
      );
      console.log(
        "SUBMIT ANSWER RESPONSE STATUS:",
        response.status,
        "ID:",
        response.id,
      );
      setLastAnswer(response);

      handleAnswerTransitions(response);
    } catch (err: any) {
      console.error("SUBMIT ANSWER ERROR:", err.message, err.detail);
      setErrorMsg(
        te(err.message) || "Failed to submit answer. Please try again.",
      );
      setErrorIsFieldLevel(err?.status === 422 || err?.status === 400);
      setStep("answering");
    }
  };

  const handleAnswerTransitions = (ans: AnswerResponse) => {
    if (ans.status === "needs_clarification") {
      setClarifyValues({});
      setStep("needs_clarification");
    } else if (ans.status === "awaiting_confirmation") {
      setStep("awaiting_confirmation");
    } else if (ans.status === "confirmed") {
      setStep("loading");
      fetchNextQuestion();
    } else if (ans.status === "draft" && ans.validationStatus === "invalid") {
      setErrorMsg(t("invalidAnswer"));
      setStep("answering");
    } else {
      setStep("answering");
    }
  };

  const handleClarifySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lastAnswer || step === "submitting") return;

    try {
      setStep("submitting");
      setErrorMsg(null);

      const response = await submitClarification(
        sessionId,
        lastAnswer.id,
        clarifyValues,
      );
      setLastAnswer(response);

      handleAnswerTransitions(response);
    } catch (err: any) {
      setErrorMsg(te(err.message) || "Failed to submit clarification details.");
      setStep("needs_clarification");
    }
  };

  const handleConfirmClick = useCallback(async () => {
    if (!lastAnswer || step === "submitting") return;

    try {
      setStep("submitting");
      setErrorMsg(null);

      console.log("CONFIRMING ANSWER ID:", lastAnswer.id);
      await confirmAnswer(sessionId, lastAnswer.id);
      console.log("CONFIRM ANSWER SUCCESS");

      setStep("loading");
      await fetchNextQuestion();
    } catch (err: any) {
      console.error("CONFIRM ANSWER ERROR:", err.message, err.detail);
      setErrorMsg(te(err.message) || "Failed to confirm values.");
      setErrorIsFieldLevel(false);
      setStep("awaiting_confirmation");
    }
  }, [lastAnswer, step, sessionId, fetchNextQuestion, te]);

  const [signatureValue, setSignatureValue] = useState<SignatureValue | null>(
    null,
  );

  const handleSignatureSubmit = async () => {
    if (!currentField || !signatureValue || step === "submitting") return;
    try {
      setStep("submitting");
      setErrorMsg(null);
      setErrorIsFieldLevel(false);
      const response = await submitSignature(
        sessionId,
        currentField.fieldId,
        signatureValue,
      );
      setLastAnswer(response);
      handleAnswerTransitions(response);
    } catch (err: any) {
      setErrorMsg(te(err.message) || "Failed to save signature.");
      setErrorIsFieldLevel(err?.status === 422);
      setStep("answering");
    }
  };

  const handleSignAfterPrinting = async () => {
    if (!currentField || step === "submitting") return;
    try {
      setStep("submitting");
      setErrorMsg(null);
      await signAfterPrinting(sessionId, currentField.fieldId);
      setSignatureValue(null);
      setStep("loading");
      await fetchNextQuestion();
    } catch (err: any) {
      setErrorMsg(te(err.message) || "Failed to record manual signing.");
      setStep("answering");
    }
  };

  const handleSkipClick = async () => {
    if (!currentField || step === "submitting") return;
    try {
      setStep("submitting");
      setErrorMsg(null);
      setErrorIsFieldLevel(false);
      await skipField(sessionId, currentField.fieldId);
      setInputValue("");
      setStep("loading");
      await fetchNextQuestion();
    } catch (err: any) {
      console.error("SKIP ANSWER ERROR:", err.message, err.detail);
      setErrorMsg(te(err.message) || "Could not skip this question.");
      setErrorIsFieldLevel(false);
      setStep("answering");
    }
  };

  const handleEditClick = useCallback(() => {
    setStep("answering");
  }, []);

  useEffect(() => {
    if (step !== "awaiting_confirmation") return;
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return;

      if (e.key === "Enter") {
        e.preventDefault();
        handleConfirmClick();
      } else if (e.key === "Escape") {
        e.preventDefault();
        handleEditClick();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [step, handleConfirmClick, handleEditClick]);

  const handleBackClick = async () => {
    if (!currentField || step === "submitting") return;

    try {
      setStep("loading");
      setErrorMsg(null);

      const prev = await previousField(sessionId);
      setCurrentFieldData(prev);
      setShowExplanation(false);
      if (prev.allFieldKeys) {
        setAllFieldKeys(prev.allFieldKeys);
      }
      setInputValue(
        prev.currentAnswerStatus ? prev.originalAnswer || "" : "",
      );
      if (
        prev.fieldType === "signature" &&
        prev.currentAnswerStatus &&
        prev.normalizedValue &&
        typeof prev.normalizedValue === "object" &&
        Array.isArray((prev.normalizedValue as any).strokes)
      ) {
        setSignatureValue(prev.normalizedValue as SignatureValue);
      } else {
        setSignatureValue(null);
      }
      setStep("answering");
    } catch (err: any) {
      setErrorMsg(te(err.message) || "Failed to navigate to previous field.");
      setStep("answering");
    }
  };

  const handleRestart = () => {
    removeSessionToken(sessionId);
    router.push("/application");
  };

  const rowContext = currentField ? parseRowKey(currentField.fieldKey) : null;
  const rowProgress = currentField
    ? rowProgressFor(currentField.fieldKey, allFieldKeys)
    : null;

  const requiredness = currentField
    ? resolveRequiredness(currentField)
    : "unknown";

  const skippable = currentField ? canSkipQuestion(currentField) : false;

  const total =
    currentField?.progress?.totalQuestions ??
    currentField?.progress?.totalRequiredFields ??
    0;
  const completed =
    currentField?.progress?.answeredQuestions ??
    currentField?.progress?.confirmedRequiredFields ??
    0;
  const progressPercent = currentField?.progress?.percentage || 0;

  if (step === "loading") {
    return (
      <main className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center text-slate-900">
        <div className="flex flex-col items-center gap-3">
          <div className="h-9 w-9 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600" />
          <p className="text-sm font-medium text-slate-600">{tc("loading")}</p>
        </div>
      </main>
    );
  }

  if (step === "error") {
    return (
      <main className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-4 text-slate-900">
        <div className="surface-panel w-full max-w-md rounded-2xl p-8 text-center">
          <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-full border border-rose-200 bg-rose-50 text-rose-600">
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-slate-900">Error Occurred</h2>
          <p className="mt-2 text-sm text-slate-600">
            {errorMsg || "An unexpected error occurred."}
          </p>
          <button
            onClick={handleRestart}
            className="btn-secondary mt-6 w-full py-3 text-sm font-semibold"
          >
            {tc("restart")}
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col justify-center px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-5xl flex-1 flex flex-col justify-center py-2">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Form Context Sidebar (desktop) */}
          <aside className="hidden lg:flex lg:col-span-4 flex-col gap-4 sticky top-20">
            {/* Form Info Card */}
            <div className="surface-card rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
                  Assisted Session
                </span>
                <span className="text-xs font-mono text-slate-500 tabular-nums">Step 2 of 4</span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <svg className="h-4 w-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Official Form Flow
                </h3>
                <p className="mt-1.5 text-xs text-slate-600 leading-relaxed">
                  Fill in your answers sequentially. Each response is standardized and verified for the official document.
                </p>
              </div>

              <div className="border-t border-slate-200 pt-3.5 space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-600">
                  <span>Questions Completed</span>
                  <span className="font-bold text-slate-900 tabular-nums">
                    {completed} of {total}
                  </span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden border border-slate-200">
                  <div
                    className="h-full rounded-full bg-indigo-600 transition-all duration-300"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Live Document Field Location Preview Card */}
            {currentField && (
              <div
                data-testid="document-location-preview"
                className="surface-card rounded-2xl p-5 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-700 flex items-center gap-1.5">
                    <svg className="h-3.5 w-3.5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                    </svg>
                    Document Placement
                  </span>
                  <span className="rounded-md bg-slate-100 border border-slate-200 px-2 py-0.5 text-[10px] font-mono font-semibold text-slate-700 tabular-nums">
                    Page {currentField.pageNumber ?? 1}
                    {currentField.sourceDocumentPageCount
                      ? ` / ${currentField.sourceDocumentPageCount}`
                      : ""}
                  </span>
                </div>

                {(() => {
                  const activePage = currentField.pageNumber ?? 1;
                  const previewUrl = pagePreviewUrls[activePage];
                  const pageW = currentField.pageWidthPt || 595;
                  const pageH = currentField.pageHeightPt || 842;
                  const box = currentField.inputBoundingBox;

                  const topPct = box
                    ? Math.min(Math.max((box.y / pageH) * 100, 1), 96)
                    : Math.min(
                        Math.max(18 + (completed / Math.max(total, 1)) * 64, 18),
                        82,
                      );
                  const leftPct = box
                    ? Math.min(Math.max((box.x / pageW) * 100, 1), 94)
                    : 10;
                  const widthPct = box
                    ? Math.min(Math.max((box.width / pageW) * 100, 2), 96 - leftPct)
                    : 80;
                  const heightPct = box
                    ? Math.min(Math.max((box.height / pageH) * 100, 1.4), 30)
                    : 5;

                  if (previewUrl) {
                    return (
                      <div className="space-y-2">
                        <button
                          type="button"
                          data-testid="enlarge-pdf-preview"
                          onClick={() => setZoomedPreviewOpen(true)}
                          className="group relative mx-auto block w-full overflow-hidden rounded-xl border border-slate-300 bg-white shadow-xs transition-all hover:border-indigo-500 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          title="Click to enlarge official PDF page"
                        >
                          <img
                            src={previewUrl}
                            alt={`Official PDF page ${activePage}`}
                            className="block w-full h-auto select-none"
                          />
                          <div
                            data-testid="pdf-field-highlight-box"
                            style={{
                              top: `${topPct}%`,
                              left: `${leftPct}%`,
                              width: `${widthPct}%`,
                              height: `${heightPct}%`,
                            }}
                            className="pointer-events-none absolute rounded-xs border-2 border-indigo-600 bg-indigo-500/25 shadow-[0_0_0_2px_rgba(79,70,229,0.25)] transition-all duration-300"
                          />
                          <span className="absolute bottom-2 end-2 rounded-md bg-slate-900/75 px-2 py-0.5 text-[10px] font-semibold text-white opacity-0 transition-opacity group-hover:opacity-100">
                            Click to enlarge
                          </span>
                        </button>
                      </div>
                    );
                  }

                  return (
                    <div className="relative mx-auto h-36 w-28 rounded-lg border border-slate-300 bg-white shadow-2xs overflow-hidden p-2">
                      <div className="h-2 w-12 rounded-xs bg-slate-300 mb-2" />
                      <div className="space-y-1.5">
                        <div className="h-1 w-full rounded-xs bg-slate-100" />
                        <div className="h-1 w-5/6 rounded-xs bg-slate-100" />
                        <div className="h-1 w-full rounded-xs bg-slate-100" />
                        <div className="h-1 w-4/5 rounded-xs bg-slate-100" />
                        <div className="h-1 w-full rounded-xs bg-slate-100" />
                        <div className="h-1 w-3/4 rounded-xs bg-slate-100" />
                      </div>
                      <div
                        style={{
                          top: `${topPct}%`,
                          left: `${leftPct}%`,
                          width: `${widthPct}%`,
                        }}
                        className="absolute h-4 rounded-xs border-2 border-indigo-600 bg-indigo-500/20 flex items-center px-1 transition-all duration-300"
                      >
                        <span className="h-1.5 w-1.5 rounded-full bg-indigo-600 shrink-0" />
                      </div>
                    </div>
                  );
                })()}

                <p className="text-[11px] text-slate-600 leading-snug text-center">
                  {currentField.sourceDocumentFilename ? (
                    <>
                      Mapped to{" "}
                      <span className="font-semibold text-slate-800">
                        {currentField.sourceDocumentFilename}
                      </span>
                    </>
                  ) : (
                    <>
                      Active field{" "}
                      <span className="font-mono font-semibold text-slate-800">
                        #{completed + 1}
                      </span>{" "}
                      on official PDF template
                    </>
                  )}
                </p>
              </div>
            )}

            {/* Multilingual Normalization Guidance Card */}
            <div className="surface-card rounded-2xl p-5 space-y-2">
              <div className="flex items-center gap-2 text-indigo-600">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                </svg>
                <h4 className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">
                  Multilingual Normalization
                </h4>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Answer in your own language. Your original wording is preserved while canonical dates, currencies, and choices are formatted for the target form.
              </p>
            </div>

            {/* Privacy Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 flex items-center gap-3 shadow-2xs">
              <div className="h-8 w-8 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700 shrink-0">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <div className="text-xs text-slate-600 leading-snug">
                <span className="font-semibold text-slate-900 block">Zero-Retention Guarantee</span>
                Your session is temporary and protected by ownership credentials.
              </div>
            </div>
          </aside>

          {/* Right Column: Active Guided Form Card */}
          <div className="lg:col-span-8 flex flex-col justify-center w-full">
            <ClaimBanner sessionId={sessionId} />

            {/* Progress header */}
            {currentField && (
              <div className="mb-5 w-full space-y-2">
                <div className="flex justify-between items-center text-xs font-semibold text-slate-700">
                  <span className="flex items-center gap-2 tabular-nums">
                    <span className="h-2 w-2 rounded-full bg-indigo-600" />
                    {t("progress", {
                      current: completed + 1,
                      total,
                      percent: progressPercent,
                    })}
                  </span>
                  <span className="rounded-md bg-indigo-50 border border-indigo-200 px-2 py-0.5 text-indigo-700 font-bold tabular-nums">
                    {progressPercent}%
                  </span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-200/80 overflow-hidden border border-slate-300/60">
                  <div
                    className="h-full rounded-full bg-indigo-600 transition-all duration-300 ease-out"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>
            )}

            <div className="surface-panel rounded-2xl p-6 sm:p-8">
              {currentField && (
                <div className="space-y-6">
                  {errorMsg && !errorIsFieldLevel && (
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

                  {/* 1. Clarification Form */}
                  {step === "needs_clarification" && lastAnswer?.clarification && (
                    <form onSubmit={handleClarifySubmit} className="space-y-6">
                      <div className="space-y-1">
                        <div className="inline-flex items-center gap-2 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
                          <span className="h-1.5 w-1.5 rounded-full bg-amber-600" />
                          Clarification Needed
                        </div>
                        <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mt-2">
                          {t("clarificationTitle")}
                        </h2>
                        <p className="text-sm text-slate-600">
                          {t("clarificationSubtitle")}
                        </p>
                      </div>

                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-1.5 text-start">
                        <p className="text-[11px] uppercase tracking-wider font-semibold text-slate-500">
                          {t("originalAnswerLabel")}
                        </p>
                        <p className="text-sm text-slate-900 font-medium">
                          &ldquo;
                          {formatOriginalAnswer(
                            inputValue,
                            currentField?.fieldType,
                            currentField?.options
                          )}
                          &rdquo;
                        </p>
                      </div>

                      <div className="space-y-4">
                        {lastAnswer.clarification.missing.map((key) => {
                          const isSentenceReason =
                            key.includes(" ") && key.length > 25;
                          return (
                            <div key={key} className="space-y-2 text-start">
                              {isSentenceReason ? (
                                <>
                                  <p className="rounded-lg border border-amber-200 bg-amber-50/70 px-3.5 py-2.5 text-xs leading-relaxed text-amber-900">
                                    {key}
                                  </p>
                                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                                    {currentField?.label || t("yourAnswerLabel")}
                                  </label>
                                </>
                              ) : (
                                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                                  {key.replace(/_/g, " ")}
                                </label>
                              )}
                              {key === "currency" ? (
                                <div className="relative">
                                  <select
                                    className="input-field pe-10 appearance-none"
                                    value={clarifyValues[key] || ""}
                                    onChange={(e) =>
                                      setClarifyValues({
                                        ...clarifyValues,
                                        [key]: e.target.value,
                                      })
                                    }
                                    required
                                  >
                                    <option value="" disabled className="bg-white text-slate-400">
                                      Select currency...
                                    </option>
                                    <option value="EUR" className="bg-white text-slate-900">EUR (€)</option>
                                    <option value="USD" className="bg-white text-slate-900">USD ($)</option>
                                    <option value="GBP" className="bg-white text-slate-900">GBP (£)</option>
                                  </select>
                                  <div className="pointer-events-none absolute inset-y-0 end-0 flex items-center px-3.5 text-slate-500">
                                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                  </div>
                                </div>
                              ) : key === "period" ? (
                                <div className="relative">
                                  <select
                                    className="input-field pe-10 appearance-none"
                                    value={clarifyValues[key] || ""}
                                    onChange={(e) =>
                                      setClarifyValues({
                                        ...clarifyValues,
                                        [key]: e.target.value,
                                      })
                                    }
                                    required
                                  >
                                    <option value="" disabled className="bg-white text-slate-400">
                                      Select frequency...
                                    </option>
                                    <option value="monthly" className="bg-white text-slate-900">Monthly</option>
                                    <option value="yearly" className="bg-white text-slate-900">Yearly</option>
                                    <option value="weekly" className="bg-white text-slate-900">Weekly</option>
                                  </select>
                                  <div className="pointer-events-none absolute inset-y-0 end-0 flex items-center px-3.5 text-slate-500">
                                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                  </div>
                                </div>
                              ) : (
                                <input
                                  type="text"
                                  className="input-field"
                                  value={clarifyValues[key] || ""}
                                  onChange={(e) =>
                                    setClarifyValues({
                                      ...clarifyValues,
                                      [key]: e.target.value,
                                    })
                                  }
                                  required
                                />
                              )}
                            </div>
                          );
                        })}
                      </div>

                      <div className="flex gap-3 pt-2">
                        <button
                          type="button"
                          onClick={handleEditClick}
                          className="btn-secondary flex-1 py-3.5 text-sm font-medium"
                        >
                          {tc("edit")}
                        </button>
                        <button
                          type="submit"
                          className="btn-primary flex-1 py-3.5 text-sm font-semibold"
                        >
                          {tc("submit")}
                        </button>
                      </div>
                    </form>
                  )}

                  {/* 2. Normalization Confirmation Screen */}
                  {step === "awaiting_confirmation" && lastAnswer && (
                    <div className="space-y-6">
                      <div className="space-y-1">
                        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
                          <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
                          Value Standardized
                        </div>
                        <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight mt-2">
                          {t("confirmTitle")}
                        </h2>
                        <p className="text-xs text-slate-600">
                          Please confirm that the standardized value matches your intention
                        </p>
                      </div>

                      <div className="space-y-3">
                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-1.5 text-start">
                          <p className="text-[11px] uppercase tracking-wider font-semibold text-slate-500">
                            {t("originalAnswerLabel")}
                          </p>
                          <p className="text-sm text-slate-800 font-medium">
                            &ldquo;
                            {currentField?.fieldType === "signature"
                              ? formatOriginalAnswer(
                                  inputValue,
                                  currentField?.fieldType,
                                  currentField?.options
                                ) || "Hand-drawn signature"
                              : formatOriginalAnswer(
                                  inputValue,
                                  currentField?.fieldType,
                                  currentField?.options
                                )}
                            &rdquo;
                          </p>
                        </div>

                        <div className="rounded-xl border border-indigo-200 bg-indigo-50/70 p-5 space-y-2 text-start">
                          <div className="flex items-center justify-between">
                            <p className="text-[11px] uppercase font-bold text-indigo-700 tracking-wider">
                              {t("proposedValueLabel")}
                            </p>
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                              </svg>
                              Ready for Form
                            </span>
                          </div>
                          {currentField?.fieldType === "signature" &&
                          lastAnswer.normalizedValue &&
                          typeof lastAnswer.normalizedValue === "object" &&
                          Array.isArray(
                            (lastAnswer.normalizedValue as any).strokes
                          ) ? (
                            <div className="space-y-2 pt-1">
                              <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                                <svg
                                  viewBox={`0 0 ${(lastAnswer.normalizedValue as any).width || 600} ${(lastAnswer.normalizedValue as any).height || 200}`}
                                  className="h-24 w-full"
                                  aria-label="Signature preview"
                                >
                                  {(
                                    (lastAnswer.normalizedValue as any)
                                      .strokes as Array<Array<[number, number]>>
                                  ).map((stroke, idx) =>
                                    stroke.length > 0 ? (
                                      <polyline
                                        key={idx}
                                        fill="none"
                                        stroke="#0f172a"
                                        strokeWidth={2.75}
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        points={stroke
                                          .map(([x, y]) => `${x},${y}`)
                                          .join(" ")}
                                      />
                                    ) : null
                                  )}
                                </svg>
                              </div>
                              <p className="text-xs font-medium text-slate-600">
                                {formatProposedValue(
                                  lastAnswer.normalizedValue,
                                  lastAnswer.outputValue,
                                  currentField?.fieldType
                                )}
                              </p>
                            </div>
                          ) : (
                            <p className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                              {formatProposedValue(
                                lastAnswer.normalizedValue,
                                lastAnswer.outputValue,
                                currentField?.fieldType
                              )}
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="flex gap-3 pt-2">
                        <button
                          type="button"
                          onClick={handleEditClick}
                          className="btn-secondary flex-1 py-3.5 text-sm font-medium"
                        >
                          <span>{tc("edit")}</span>
                          <kbd className="hidden sm:inline-block rounded bg-slate-100 border border-slate-300 px-1.5 py-0.5 text-[10px] font-mono text-slate-600">Esc</kbd>
                        </button>
                        <button
                          type="button"
                          onClick={handleConfirmClick}
                          className="btn-primary flex-1 py-3.5 text-sm font-semibold"
                        >
                          <span>{tc("confirm")}</span>
                          <kbd className="hidden sm:inline-block rounded bg-indigo-700 border border-indigo-500 px-1.5 py-0.5 text-[10px] font-mono text-indigo-100">↵ Enter</kbd>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* 3. Primary Answering Flow */}
                  {(step === "answering" || step === "submitting") && (
                    <form onSubmit={handleSubmitAnswer} className="space-y-6">
                      <div className="space-y-2 text-start">
                        {rowContext && (
                          <p
                            data-testid="row-context"
                            className="text-xs font-bold uppercase tracking-wider text-indigo-700"
                          >
                            {rowHeading(rowContext.section, rowContext.index)}
                            {rowProgress && (
                              <span
                                data-testid="row-progress"
                                className="ms-2 font-medium text-slate-500 tabular-nums"
                              >
                                {t("rowFieldProgress", {
                                  position: rowProgress.position,
                                  total: rowProgress.total,
                                })}
                              </span>
                            )}
                          </p>
                        )}
                        <div className="flex items-start justify-between gap-3">
                          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight leading-snug">
                            {currentField.label}
                            {requiredness === "required" && (
                              <span className="ms-1 text-rose-600" aria-hidden="true">
                                *
                              </span>
                            )}
                          </h2>
                          {requiredness !== "unknown" && (
                            <span
                              className={`shrink-0 rounded-md px-2.5 py-0.5 text-xs font-semibold ${
                                requiredness === "required"
                                  ? "bg-rose-50 text-rose-700 border border-rose-200"
                                  : "bg-slate-100 text-slate-700 border border-slate-200"
                              }`}
                              data-testid="requiredness"
                            >
                              {requiredness === "required"
                                ? t("required")
                                : t("optional")}
                            </span>
                          )}
                        </div>

                        {currentField.fieldExplanation && (
                          <div className="pt-1">
                            <button
                              type="button"
                              data-testid="toggle-field-explanation"
                              aria-expanded={showExplanation}
                              onClick={() => setShowExplanation((prev) => !prev)}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50/70 px-3 py-1.5 text-xs font-semibold text-indigo-700 transition-colors hover:bg-indigo-100/80"
                            >
                              <svg
                                className="h-3.5 w-3.5 text-indigo-600 shrink-0"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                />
                              </svg>
                              <span>
                                {showExplanation
                                  ? t("hideExplainButton")
                                  : t("explainButton")}
                              </span>
                            </button>

                            {showExplanation && (
                              <div
                                data-testid="field-explanation-panel"
                                className="mt-3 rounded-xl border border-indigo-200/80 bg-indigo-50/50 p-4 space-y-3 text-start"
                              >
                                <div>
                                  <p className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">
                                    {t("whatThisMeans")}
                                  </p>
                                  <p className="mt-0.5 text-xs leading-relaxed text-slate-800">
                                    {currentField.fieldExplanation.summary}
                                  </p>
                                </div>
                                <div className="border-t border-indigo-200/60 pt-2.5">
                                  <p className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">
                                    {t("whereToFindIt")}
                                  </p>
                                  <p className="mt-0.5 text-xs leading-relaxed text-slate-700">
                                    {currentField.fieldExplanation.whereToFind}
                                  </p>
                                </div>
                                {currentField.fieldExplanation.example && (
                                  <div className="border-t border-indigo-200/60 pt-2.5 flex items-center gap-2">
                                    <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">
                                      {t("exampleAnswer")}:
                                    </span>
                                    <code className="rounded bg-white border border-indigo-200 px-2 py-0.5 text-xs font-mono font-semibold text-slate-900">
                                      {currentField.fieldExplanation.example}
                                    </code>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {currentField.fieldType === "signature" ? (
                        <SignaturePad
                          key={currentField.fieldId}
                          fieldKey={currentField.key}
                          value={signatureValue}
                          onChange={setSignatureValue}
                          onSignAfterPrinting={handleSignAfterPrinting}
                          pendingManualSignature={
                            currentField.currentAnswerStatus ===
                            "pending_manual_signature"
                          }
                          disabled={step === "submitting"}
                          error={errorIsFieldLevel ? errorMsg || undefined : undefined}
                        />
                      ) : (
                        <FieldRenderer
                          fieldType={currentField.fieldType}
                          fieldKey={currentField.key}
                          required={requiredness === "required"}
                          configuration={{}}
                          options={currentField.options || []}
                          value={inputValue}
                          placeholder={currentField.placeholder || ""}
                          helpText={currentField.helpText || ""}
                          enableVoiceInput={true}
                          error={
                            errorIsFieldLevel ? errorMsg || undefined : undefined
                          }
                          onChange={(val) => {
                            setErrorMsg(null);
                            setInputValue(val);
                          }}
                        />
                      )}

                      {/* Footer navigation */}
                      <div className="flex gap-3 pt-4 border-t border-slate-200">
                        <button
                          type="button"
                          disabled={
                            currentField.position === 1 || step === "submitting"
                          }
                          onClick={handleBackClick}
                          className="btn-secondary flex-1 py-3.5 text-sm font-medium"
                        >
                          <svg className="h-4 w-4 rtl:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                          </svg>
                          <span>{tc("back")}</span>
                        </button>
                        {skippable && (
                          <button
                            type="button"
                            disabled={step === "submitting"}
                            onClick={handleSkipClick}
                            data-testid="skip-question"
                            className="btn-secondary flex-1 py-3.5 text-sm font-medium"
                          >
                            {t("skipQuestion")}
                          </button>
                        )}
                        <button
                          type={
                            currentField.fieldType === "signature"
                              ? "button"
                              : "submit"
                          }
                          onClick={
                            currentField.fieldType === "signature"
                              ? handleSignatureSubmit
                              : undefined
                          }
                          disabled={
                            currentField.fieldType === "signature"
                              ? signatureValue === null || step === "submitting"
                              : !inputValue.trim() || step === "submitting"
                          }
                          className="btn-primary flex-1 py-3.5 text-sm font-semibold"
                        >
                          <span>{step === "submitting" ? tc("loading") : tc("continue")}</span>
                          {step !== "submitting" && (
                            <svg className="h-4 w-4 rtl:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          )}
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Full-Resolution PDF Page Zoom Modal */}
      {zoomedPreviewOpen &&
        currentField &&
        pagePreviewUrls[currentField.pageNumber ?? 1] && (
          <div
            data-testid="pdf-preview-modal"
            onClick={() => setZoomedPreviewOpen(false)}
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 p-4 backdrop-blur-xs"
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="relative flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
            >
              <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3.5">
                <div className="space-y-0.5 text-start">
                  <p className="text-xs font-bold uppercase tracking-wider text-indigo-700">
                    Official Document Placement • Page {currentField.pageNumber ?? 1}
                  </p>
                  <p className="text-sm font-bold text-slate-900 truncate">
                    {currentField.label}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setZoomedPreviewOpen(false)}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Close
                </button>
              </div>
              <div className="overflow-y-auto p-4 sm:p-6 bg-slate-100/70">
                {(() => {
                  const activePage = currentField.pageNumber ?? 1;
                  const previewUrl = pagePreviewUrls[activePage];
                  const pageW = currentField.pageWidthPt || 595;
                  const pageH = currentField.pageHeightPt || 842;
                  const box = currentField.inputBoundingBox;
                  const topPct = box
                    ? Math.min(Math.max((box.y / pageH) * 100, 1), 96)
                    : 20;
                  const leftPct = box
                    ? Math.min(Math.max((box.x / pageW) * 100, 1), 94)
                    : 10;
                  const widthPct = box
                    ? Math.min(
                        Math.max((box.width / pageW) * 100, 2),
                        96 - leftPct,
                      )
                    : 80;
                  const heightPct = box
                    ? Math.min(Math.max((box.height / pageH) * 100, 1.4), 30)
                    : 5;

                  return (
                    <div className="relative mx-auto w-fit h-fit rounded-lg border border-slate-300 bg-white shadow-md">
                      <img
                        src={previewUrl}
                        alt={`Official PDF page ${activePage} enlarged`}
                        className="block max-w-full h-auto rounded-lg select-none"
                      />
                      <div
                        style={{
                          top: `${topPct}%`,
                          left: `${leftPct}%`,
                          width: `${widthPct}%`,
                          height: `${heightPct}%`,
                        }}
                        className="pointer-events-none absolute rounded-xs border-2 border-indigo-600 bg-indigo-500/25 shadow-[0_0_0_4px_rgba(79,70,229,0.28)]"
                      />
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        )}
    </main>
  );
}
