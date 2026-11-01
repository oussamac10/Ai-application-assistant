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
import ClaimBanner from "@/features/applications/components/ClaimBanner";
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
  const [zoomedPreviewOpen, setZoomedPreviewOpen] = useState<boolean>(false);
  const [signatureValue, setSignatureValue] = useState<SignatureValue | null>(
    null,
  );
  const pagePreviewUrlsRef = useRef<Record<number, string>>({});

  useEffect(() => {
    const activePage = currentField?.pageNumber ?? 1;
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
          <SessionContextSidebar
            currentField={currentField}
            completed={completed}
            total={total}
            progressPercent={progressPercent}
            pagePreviewUrls={pagePreviewUrls}
            zoomedPreviewOpen={zoomedPreviewOpen}
            onOpenZoom={() => setZoomedPreviewOpen(true)}
            onCloseZoom={() => setZoomedPreviewOpen(false)}
          />

          {/* Right Column: Active Guided Form Card */}
          <div className="lg:col-span-8 flex flex-col justify-center w-full">
            <ClaimBanner sessionId={sessionId} />

            {auth?.user && (
              <div className="mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 rounded-xl border border-indigo-200/80 bg-white px-4 py-3 shadow-2xs text-start">
                <span className="text-xs font-medium text-slate-700">
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
                      <svg
                        className="h-4 w-4 text-rose-600 shrink-0"
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
                            {formatFieldLabel(currentField.label)}
                            {requiredness === "required" && (
                              <span
                                className="ms-1 text-rose-600"
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
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-indigo-200 bg-indigo-50/70 p-4 text-start">
                            <div className="space-y-0.5 min-w-0">
                              <p className="text-xs font-semibold text-indigo-800">
                                {t("prefilledReviewLabel")}
                              </p>
                              <p className="text-sm font-bold text-slate-900 break-words">
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
                      <div className="flex gap-3 pt-4 border-t border-slate-200">
                        <button
                          type="button"
                          disabled={
                            isFirstField || step === "submitting"
                          }
                          onClick={handleBackClick}
                          className="btn-secondary flex-1 py-3.5 text-sm font-medium"
                        >
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
                              d="M15 19l-7-7 7-7"
                            />
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
                          <span>
                            {step === "submitting"
                              ? tc("loading")
                              : tc("continue")}
                          </span>
                          {step !== "submitting" && (
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
                                d="M9 5l7 7-7 7"
                              />
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
    </main>
  );
}
