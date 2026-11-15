"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  startSession,
  getSession,
  getCurrentField,
  fetchSessionPagePreviewBlob,
  skipField,
  submitSignature,
  signAfterPrinting,
  submitAnswer,
  submitClarification,
  confirmAnswer,
  previousField,
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
import { formatProposedValue } from "@/features/form-session/utils/formatProposedValue";
import { formatFieldLabel } from "@/features/form-session/utils/formatFieldLabel";
import { SessionContextSidebar } from "@/features/form-session/components/SessionContextSidebar";
import { SessionClarificationPanel } from "@/features/form-session/components/SessionClarificationPanel";
import { SessionConfirmationPanel } from "@/features/form-session/components/SessionConfirmationPanel";
import { SessionFieldExplanation } from "@/features/form-session/components/SessionFieldExplanation";
import { TableRowGroupCard } from "@/features/form-session/components/TableRowGroupCard";
import ClaimBanner from "@/features/applications/components/ClaimBanner";
import { SaveAndResumeModal } from "@/features/applications/components/SaveAndResumeModal";
import {
  Bookmark,
  Loader2,
  AlertTriangle,
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  ClipboardCheck,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useSafeAuth } from "@/features/auth/hooks/useSafeAuth";
import { prefillSessionFromVault } from "@/features/profile-vault/services/vaultClient";

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

  const auth = useSafeAuth();
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
  const [clarifyValues, setClarifyValues] = useState<Record<string, string>>({});
  const [showExplanation, setShowExplanation] = useState<boolean>(false);
  const [prefilling, setPrefilling] = useState<boolean>(false);
  const [vaultNotice, setVaultNotice] = useState<string | null>(null);
  const [pagePreviewUrls, setPagePreviewUrls] = useState<Record<number, string>>({});
  const [previewPage, setPreviewPage] = useState<number>(1);
  const [zoomedPreviewOpen, setZoomedPreviewOpen] = useState<boolean>(false);
  const [forceSingleFieldMode, setForceSingleFieldMode] = useState<boolean>(false);
  const [signatureValue, setSignatureValue] = useState<SignatureValue | null>(
    null,
  );
  const [isSaveResumeOpen, setIsSaveResumeOpen] = useState<boolean>(false);
  const [requiredDocuments, setRequiredDocuments] = useState<string[]>([]);
  const [prepDocsChecked, setPrepDocsChecked] = useState<Record<number, boolean>>({});
  const [prepBannerExpanded, setPrepBannerExpanded] = useState<boolean>(false);
  const [slideDirection, setSlideDirection] = useState<"forward" | "backward">("forward");
  const lastPosRef = useRef<number>(0);
  const pagePreviewUrlsRef = useRef<Record<number, string>>({});

  useEffect(() => {
    if (currentField) {
      const currentPos = currentField.position ?? 0;
      if (currentPos < lastPosRef.current) {
        setSlideDirection("backward");
      } else {
        setSlideDirection("forward");
      }
      lastPosRef.current = currentPos;
    }
  }, [currentField]);

  useEffect(() => {
    if (currentField?.pageNumber) {
      setPreviewPage(currentField.pageNumber);
    }
    setForceSingleFieldMode(false);
  }, [currentField?.fieldKey, currentField?.pageNumber]);

  useEffect(() => {
    const activePage = previewPage || currentField?.pageNumber || 1;
    if (!sessionId) return;
    if (!currentField?.sourceDocumentFilename) return;
    if (typeof fetchSessionPagePreviewBlob !== "function") return;
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
  }, [sessionId, previewPage, currentField?.pageNumber, currentField?.sourceDocumentFilename]);

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
        Array.isArray((field.normalizedValue as { strokes?: unknown }).strokes)
      ) {
        setSignatureValue(field.normalizedValue as SignatureValue);
      } else {
        setSignatureValue(null);
      }

      setStep("answering");
    } catch (err: unknown) {
      const code = err instanceof Error ? err.message : "unavailable";
      setErrorMsg(te(code) || "Failed to retrieve next form question.");
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

        try {
          if (typeof getSession === "function") {
            Promise.resolve(getSession(sessionId))
              .then((sessionMeta) => {
                if (sessionMeta?.requiredDocuments?.length) {
                  setRequiredDocuments(sessionMeta.requiredDocuments);
                }
              })
              .catch(() => {});
          }
        } catch {
          // Ignored when test mocks omit optional getSession metadata helper
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

  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentField || !inputValue.trim() || step === "submitting") return;

    try {
      setStep("submitting");
      setErrorMsg(null);
      setErrorIsFieldLevel(false);

      const response = await submitAnswer(
        sessionId,
        currentField.fieldId,
        inputValue,
      );
      setLastAnswer(response);

      handleAnswerTransitions(response);
    } catch (err: any) {
      setErrorMsg(
        te(err.message) || "Failed to submit answer. Please try again.",
      );
      setErrorIsFieldLevel(err?.status === 422 || err?.status === 400);
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

      await confirmAnswer(sessionId, lastAnswer.id);

      setStep("loading");
      await fetchNextQuestion();
    } catch (err: any) {
      setErrorMsg(te(err.message) || "Failed to confirm values.");
      setErrorIsFieldLevel(false);
      setStep("awaiting_confirmation");
    }
  }, [lastAnswer, step, sessionId, fetchNextQuestion, te]);

  const handlePrefillFromVault = async () => {
    if (prefilling || step === "submitting") return;
    try {
      setPrefilling(true);
      setErrorMsg(null);
      const res = await prefillSessionFromVault(sessionId);
      setVaultNotice(
        res.prefilledCount > 0
          ? t("prefilledCountNotice", { count: res.prefilledCount })
          : t("prefilledEmptyNotice"),
      );
      await fetchNextQuestion();
    } catch {
      setErrorMsg(
        te("unavailable") || "Could not pre-fill from Profile Vault.",
      );
    } finally {
      setPrefilling(false);
    }
  };

  const handleConfirmPrefilled = async () => {
    if (!currentField?.currentAnswerId || step === "submitting") return;
    try {
      setStep("submitting");
      setErrorMsg(null);
      await confirmAnswer(sessionId, currentField.currentAnswerId);
      setStep("loading");
      await fetchNextQuestion();
    } catch (err: any) {
      setErrorMsg(te(err.message) || "Failed to confirm pre-filled value.");
      setStep("answering");
    }
  };

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
      if (
        target &&
        (target.tagName === "INPUT" || target.tagName === "TEXTAREA")
      ) {
        return;
      }

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
        Array.isArray((prev.normalizedValue as { strokes?: unknown }).strokes)
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
  const isFirstField = currentField
    ? allFieldKeys.length > 0
      ? allFieldKeys[0] === (currentField.fieldKey || currentField.key)
      : currentField.position <= 1
    : true;

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
      <main className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center bg-[#0A0E17] text-slate-100">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-9 w-9 animate-spin text-emerald-400" />
          <p className="text-sm font-medium text-slate-400">{tc("loading")}</p>
        </div>
      </main>
    );
  }

  if (step === "error") {
    return (
      <main className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center bg-[#0A0E17] px-4 text-slate-100">
        <div className="surface-panel w-full max-w-md rounded-2xl p-8 text-center">
          <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-full border border-rose-500/30 bg-rose-500/10 text-rose-400">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <h2 className="text-lg font-bold text-white">Error Occurred</h2>
          <p className="mt-2 text-sm text-slate-400">
            {errorMsg || "An unexpected error occurred."}
          </p>
          <button
            onClick={handleRestart}
            className="btn-secondary mt-6 w-full py-3 text-sm font-semibold active:scale-[0.98] transition-all"
          >
            {tc("restart")}
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col justify-center bg-[#0A0E17] text-slate-100 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-5xl flex-1 flex flex-col justify-center py-2">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <SessionContextSidebar
            currentField={currentField}
            completed={completed}
            total={total}
            progressPercent={progressPercent}
            pagePreviewUrls={pagePreviewUrls}
            previewPage={previewPage}
            onChangePreviewPage={setPreviewPage}
            zoomedPreviewOpen={zoomedPreviewOpen}
            onOpenZoom={() => setZoomedPreviewOpen(true)}
            onCloseZoom={() => setZoomedPreviewOpen(false)}
          />

          {/* Right Column: Active Guided Form Card */}
          <div className="lg:col-span-8 flex flex-col justify-center w-full">
            <ClaimBanner
              sessionId={sessionId}
              formTitle={currentField?.sourceDocumentFilename || "Official Form"}
              completedCount={completed}
              totalCount={total}
              progressPercent={progressPercent}
            />

            {requiredDocuments.length > 0 && (
              <div
                data-testid="session-required-documents-banner"
                className="mb-4 rounded-xl border border-white/10 bg-[#0F1522] px-4 py-3 shadow-2xs text-start"
              >
                <button
                  type="button"
                  onClick={() => setPrepBannerExpanded((prev) => !prev)}
                  className="w-full flex items-center justify-between gap-3 text-xs font-semibold text-slate-200 cursor-pointer"
                >
                  <span className="flex items-center gap-2">
                    <ClipboardCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>
                      Supporting Documents Checklist ({requiredDocuments.length})
                    </span>
                  </span>
                  {prepBannerExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400 shrink-0" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
                  )}
                </button>
                {prepBannerExpanded && (
                  <ul className="mt-3 pt-3 border-t border-white/[0.08] space-y-2">
                    {requiredDocuments.map((docName, idx) => {
                      const isChecked = Boolean(prepDocsChecked[idx]);
                      return (
                        <li key={`${idx}-${docName}`}>
                          <label className="flex items-start gap-2.5 text-xs text-slate-300 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() =>
                                setPrepDocsChecked((prev) => ({
                                  ...prev,
                                  [idx]: !prev[idx],
                                }))
                              }
                              className="mt-0.5 h-3.5 w-3.5 rounded border-white/20 bg-[#0A0E17] text-emerald-500 accent-emerald-500 shrink-0 cursor-pointer"
                            />
                            <span className={isChecked ? "line-through text-emerald-400/80" : ""}>
                              {docName}
                            </span>
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            )}

            {auth?.user && (
              <div className="mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 rounded-xl border border-emerald-500/30 bg-[#0F1522] px-4 py-3 shadow-2xs text-start">
                <span className="text-xs font-medium text-slate-200">
                  {vaultNotice || t("prefillFromVault")}
                </span>
                <button
                  type="button"
                  data-testid="prefill-from-vault-btn"
                  disabled={prefilling || step === "submitting"}
                  onClick={handlePrefillFromVault}
                  className="btn-secondary shrink-0 px-3.5 py-1.5 text-xs font-semibold"
                >
                  {prefilling ? t("prefillingFromVault") : t("prefillFromVault")}
                </button>
              </div>
            )}

            {/* High-Contrast Command Header & Animated Progress Rail */}
            {currentField && (
              <div className="mb-5 w-full space-y-2.5">
                <div className="flex justify-between items-center text-xs font-semibold text-slate-300">
                  <div className="flex items-center gap-2 tabular-nums">
                    <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse motion-reduce:animate-none" />
                    <span className="font-mono text-[11px] text-slate-200 uppercase tracking-tight">
                      {t("progress", {
                        current: completed + 1,
                        total,
                        percent: progressPercent,
                      })}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {!auth?.user && (
                      <button
                        type="button"
                        onClick={() => setIsSaveResumeOpen(true)}
                        className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg border border-white/15 bg-[#0F1522] text-slate-200 hover:bg-[#151D2E] hover:border-emerald-500/40 hover:text-white transition-colors text-[11px] font-medium cursor-pointer shadow-2xs"
                        title="Save your progress to resume later"
                      >
                        <Bookmark className="w-3 h-3 text-emerald-400" />
                        <span>Save & Resume</span>
                      </button>
                    )}
                    <span className="rounded-md bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-emerald-400 font-mono font-bold tabular-nums text-xs">
                      {progressPercent}%
                    </span>
                  </div>
                </div>

                {/* Animated Step Progress Rail */}
                <div className="h-2 w-full rounded-full bg-[#151D2E] overflow-hidden border border-white/10 shadow-inner">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-400 transition-all duration-500 ease-out motion-reduce:transition-none shadow-[0_0_12px_rgba(16,185,129,0.5)] relative overflow-hidden"
                    style={{ width: `${progressPercent}%` }}
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer motion-reduce:animate-none" />
                  </div>
                </div>
              </div>
            )}

            <div
              key={currentField?.fieldId || currentField?.position}
              className={`surface-panel rounded-2xl p-6 sm:p-8 animate-in fade-in ${
                slideDirection === "backward" ? "slide-in-from-left-4" : "slide-in-from-right-4"
              } duration-200 motion-reduce:animate-none`}
            >
              {currentField && (
                <div className="space-y-6">
                  {errorMsg && !errorIsFieldLevel && (
                    <div
                      role="alert"
                      className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200 flex items-center gap-3"
                    >
                      <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
                      <span>{errorMsg}</span>
                    </div>
                  )}

                  {step === "needs_clarification" &&
                    lastAnswer?.clarification && (
                      <SessionClarificationPanel
                        currentField={currentField}
                        lastAnswer={lastAnswer}
                        inputValue={inputValue}
                        clarifyValues={clarifyValues}
                        onClarifyValuesChange={setClarifyValues}
                        onSubmit={handleClarifySubmit}
                        onEdit={handleEditClick}
                      />
                    )}

                  {step === "awaiting_confirmation" && lastAnswer && (
                    <SessionConfirmationPanel
                      currentField={currentField}
                      lastAnswer={lastAnswer}
                      inputValue={inputValue}
                      onEdit={handleEditClick}
                      onConfirm={handleConfirmClick}
                    />
                  )}

                  {(step === "answering" || step === "submitting") &&
                    !forceSingleFieldMode &&
                    currentField.tableRow &&
                    currentField.tableRow.fields.length >= 2 &&
                    currentField.fieldType !== "signature" && (
                      <TableRowGroupCard
                        sessionId={sessionId}
                        tableRow={currentField.tableRow}
                        onRowCompleted={fetchNextQuestion}
                        onSwitchToSingleField={() => setForceSingleFieldMode(true)}
                      />
                    )}

                  {(step === "answering" || step === "submitting") &&
                    (forceSingleFieldMode ||
                      !currentField.tableRow ||
                      currentField.tableRow.fields.length < 2 ||
                      currentField.fieldType === "signature") && (
                    <form onSubmit={handleSubmitAnswer} className="space-y-6">
                      <div className="space-y-2 text-start">
                        {rowContext && (
                          <p
                            data-testid="row-context"
                            className="text-xs font-bold uppercase tracking-wider text-emerald-400"
                          >
                            {rowHeading(rowContext.section, rowContext.index)}
                            {rowProgress && (
                              <span
                                data-testid="row-progress"
                                className="ms-2 font-medium text-slate-400 tabular-nums"
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
                          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight leading-snug">
                            {formatFieldLabel(currentField.label)}
                            {requiredness === "required" && (
                              <span
                                className="ms-1 text-rose-400"
                                aria-hidden="true"
                              >
                                *
                              </span>
                            )}
                          </h2>
                          {requiredness !== "unknown" && (
                            <span
                              className={`shrink-0 rounded-md px-2.5 py-0.5 text-xs font-semibold ${
                                requiredness === "required"
                                  ? "bg-rose-500/10 text-rose-300 border border-rose-500/30"
                                  : "bg-[#151D2E] text-slate-300 border border-white/10"
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
                          <SessionFieldExplanation
                            explanation={currentField.fieldExplanation}
                            open={showExplanation}
                            onToggle={() => setShowExplanation((prev) => !prev)}
                          />
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
                          error={
                            errorIsFieldLevel ? errorMsg || undefined : undefined
                          }
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

                      {currentField.currentAnswerStatus ===
                        "awaiting_confirmation" &&
                        currentField.currentAnswerId &&
                        inputValue === (currentField.originalAnswer || "") && (
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-start">
                            <div className="space-y-0.5 min-w-0">
                              <p className="text-xs font-semibold text-emerald-400">
                                {t("prefilledReviewLabel")}
                              </p>
                              <p className="text-sm font-bold text-white break-words">
                                <bdi>
                                  {formatProposedValue(
                                    currentField.normalizedValue,
                                    currentField.outputValue,
                                    currentField.fieldType,
                                  ) || currentField.originalAnswer}
                                </bdi>
                              </p>
                            </div>
                            <button
                              type="button"
                              data-testid="confirm-prefilled-btn"
                              disabled={step === "submitting"}
                              onClick={handleConfirmPrefilled}
                              className="btn-primary shrink-0 px-4 py-2 text-xs font-semibold"
                            >
                              {t("confirmPrefilled")}
                            </button>
                          </div>
                        )}

                      {/* Footer navigation */}
                      <div className="flex gap-3 pt-4 border-t border-white/10">
                        <button
                          type="button"
                          disabled={
                            isFirstField || step === "submitting"
                          }
                          onClick={handleBackClick}
                          className="btn-secondary flex-1 py-3.5 text-sm font-medium active:scale-[0.98] transition-all"
                        >
                          <ArrowLeft className="h-4 w-4 rtl:rotate-180" />
                          <span>{tc("back")}</span>
                        </button>
                        {skippable && (
                          <button
                            type="button"
                            disabled={step === "submitting"}
                            onClick={handleSkipClick}
                            data-testid="skip-question"
                            className="btn-secondary flex-1 py-3.5 text-sm font-medium active:scale-[0.98] transition-all"
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
                          className="btn-primary flex-1 py-3.5 text-sm font-semibold active:scale-[0.98] transition-all"
                        >
                          <span>
                            {step === "submitting"
                              ? tc("loading")
                              : tc("continue")}
                          </span>
                          {step !== "submitting" && (
                            <ArrowRight className="h-4 w-4 rtl:rotate-180" />
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

      <SaveAndResumeModal
        isOpen={isSaveResumeOpen}
        onClose={() => setIsSaveResumeOpen(false)}
        sessionId={sessionId}
        formTitle={currentField?.sourceDocumentFilename || "Official Form"}
        completedCount={completed}
        totalCount={total}
        progressPercent={progressPercent}
      />
    </main>
  );
}
