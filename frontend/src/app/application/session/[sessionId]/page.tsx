"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  startSession,
  getCurrentField,
  skipField,
  submitAnswer,
  submitClarification,
  confirmAnswer,
  previousField,
  changeAnswer,
  getSummary,
  CurrentField,
  AnswerResponse,
} from "@/features/form-session/services/apiClient";
import { removeSessionToken } from "@/features/form-session/services/sessionCredentials";
import { FieldRenderer } from "@/features/form-session/components/FieldRenderer";
import { formatProposedValue } from "@/features/form-session/utils/formatProposedValue";
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
  /** Whether the current error belongs to the field the user is editing.
   *
   * A validation problem is shown once, next to the input it concerns.
   * Unexpected or global failures (transport, session state) get the
   * page-level banner instead. Previously one `errorMsg` fed both, so every
   * validation message was printed twice. */
  const [errorIsFieldLevel, setErrorIsFieldLevel] = useState<boolean>(false);

  // Clarification form state
  const [clarifyValues, setClarifyValues] = useState<Record<string, any>>({});

  // Guards against firing /start more than once for the same session (React
  // 18 StrictMode double-invokes effects in dev, and fetchNextQuestion's
  // identity can change across renders since it depends on the te
  // translator function).
  const initializedSessionRef = useRef<string | null>(null);

  const fetchNextQuestion = useCallback(async () => {
    try {
      setErrorMsg(null);
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

      // Complete when every question has been answered. Keying this off
      // *required* fields alone stranded the user on a form that marks
      // nothing mandatory: zero required fields meant the summary was never
      // reached.
      const total =
        field.progress?.totalQuestions ??
        field.progress?.totalRequiredFields ??
        0;
      const completed =
        field.progress?.answeredQuestions ??
        field.progress?.confirmedRequiredFields ??
        0;
      if (total > 0 && completed >= total) {
        // Automatically direct user to the summary screen
        router.push(`/application/session/${sessionId}/summary`);
        return;
      }

      // Populate input value if there is an existing answer in summary
      if (field.currentAnswerStatus) {
        try {
          const summary = await getSummary(sessionId);
          const answerInfo = summary.fields.find(
            (f: any) => f.fieldId === field.fieldId,
          );
          if (answerInfo) {
            setInputValue(answerInfo.originalAnswer || "");
          }
        } catch {
          setInputValue("");
        }
      } else {
        setInputValue("");
      }

      setStep("answering");
    } catch (err: any) {
      console.error("FETCH NEXT QUESTION ERROR:", err.message, err.detail);
      setErrorMsg(te(err.message) || "Failed to retrieve next form question.");
      setStep("error");
    }
  }, [sessionId, router, te]);

  useEffect(() => {
    // No early credential check here: a claimed (authenticated-owned)
    // session has no anonymous ownership token in sessionStorage at all and
    // must still resume via the auth cookie alone. If access truly isn't
    // authorized, the request below fails with a 401 and surfaces the
    // normal error state instead of a client-side guess.
    if (initializedSessionRef.current === sessionId) return;
    initializedSessionRef.current = sessionId;

    async function initSession() {
      try {
        setStep("loading");
        setErrorMsg(null);

        // Start/resume session
        try {
          await startSession(sessionId);
        } catch (err: any) {
          // Ignore conflict if session is already in progress
          if (err.status !== 409) throw err;
        }

        // Fetch first question
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
      // A rejected answer is a problem with this field, not with the page.
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
      // Confirmed, advance
      setStep("loading");
      fetchNextQuestion();
    } else if (ans.status === "draft" && ans.validationStatus === "invalid") {
      // Deterministic validation rejected the value (e.g. an option not in
      // the field's configured set) — surface it instead of silently
      // resetting, so the user knows why nothing advanced.
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

  const handleConfirmClick = async () => {
    if (!lastAnswer || step === "submitting") return;

    try {
      setStep("submitting");
      setErrorMsg(null);

      console.log("CONFIRMING ANSWER ID:", lastAnswer.id);
      await confirmAnswer(sessionId, lastAnswer.id);
      console.log("CONFIRM ANSWER SUCCESS");

      // Advance to next question
      setStep("loading");
      await fetchNextQuestion();
    } catch (err: any) {
      console.error("CONFIRM ANSWER ERROR:", err.message, err.detail);
      setErrorMsg(te(err.message) || "Failed to confirm values.");
      setErrorIsFieldLevel(false);
      setStep("awaiting_confirmation");
    }
  };

  const handleSkipClick = async () => {
    if (!currentField || step === "submitting") return;
    // The backend records status="skipped" with null values and advances the
    // session. Re-fetching alone did nothing: the current-field endpoint would
    // return the same question, because nothing had moved the position.
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

  const handleEditClick = () => {
    // Returns user to answering state so they can modify input text
    setStep("answering");
  };

  const handleBackClick = async () => {
    if (!currentField || step === "submitting") return;

    try {
      setStep("loading");
      setErrorMsg(null);

      const prev = await previousField(sessionId);
      setCurrentFieldData(prev);

      // Populate previous values from summary
      if (prev.currentAnswerStatus) {
        try {
          const summary = await getSummary(sessionId);
          const answerInfo = summary.fields.find(
            (f: any) => f.fieldId === prev.fieldId,
          );
          if (answerInfo) {
            setInputValue(answerInfo.originalAnswer || "");
          }
        } catch {
          setInputValue("");
        }
      } else {
        setInputValue("");
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

  // Three states, not a boolean. A backend that has not been redeployed omits
  // the field; the legacy boolean then answers "required" or — since it cannot
  // distinguish "optional" from "nothing was said" — "unknown", which is the
  // safe reading because it neither blocks the user nor invents a claim.
  const requiredness = currentField
    ? (currentField.requiredness ?? (currentField.required ? "required" : "unknown"))
    : "unknown";

  // Progress percentage calculation
  // Count every question, not only the mandatory ones: with evidence-based
  // requiredness a form that marks nothing mandatory showed "Question 1 of 0".
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
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 text-slate-100">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-indigo-500" />
          <p className="text-sm font-medium text-slate-400">{tc("loading")}</p>
        </div>
      </main>
    );
  }

  if (step === "error") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 px-4 text-slate-100">
        <div className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900/60 p-8 text-center shadow-2xl backdrop-blur-xl">
          <div className="mb-4 text-rose-400">
            <svg
              className="mx-auto h-12 w-12"
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
          <h2 className="text-xl font-bold text-slate-200">Error Occurred</h2>
          <p className="mt-2 text-sm text-slate-400">
            {errorMsg || "An unexpected error occurred."}
          </p>
          <button
            onClick={handleRestart}
            className="mt-6 w-full rounded-xl bg-slate-800 py-3 text-sm font-bold text-slate-200 transition hover:bg-slate-700 active:scale-[0.99]"
          >
            {tc("restart")}
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 text-slate-100 px-4 py-8 sm:px-6 lg:px-8">
      {/* Central guided card container */}
      <div className="mx-auto w-full max-w-xl flex-1 flex flex-col justify-center">
        <ClaimBanner sessionId={sessionId} />
        {/* Progress header */}
        {currentField && (
          <div className="mb-6 w-full space-y-2">
            <div className="flex justify-between text-xs font-semibold tracking-wide text-slate-400">
              <span>
                {t("progress", {
                  current: completed + 1,
                  total,
                  percent: progressPercent,
                })}
              </span>
              <span>{progressPercent}%</span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-950 overflow-hidden border border-slate-850">
              <div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}

        <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/60 p-6 md:p-8 shadow-2xl backdrop-blur-xl">
          {/* Glowing orb decorative */}
          <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-indigo-500/10 blur-3xl" />

          {currentField && (
            <div className="relative z-10 space-y-6">
              {errorMsg && !errorIsFieldLevel && (
                <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300">
                  {errorMsg}
                </div>
              )}

              {/* Workflow Screens Switcher */}

              {/* 1. Clarification Form */}
              {step === "needs_clarification" && lastAnswer?.clarification && (
                <form onSubmit={handleClarifySubmit} className="space-y-6">
                  <div className="space-y-1">
                    <h2 className="text-xl font-bold text-slate-200">
                      {t("clarificationTitle")}
                    </h2>
                    <p className="text-sm text-slate-400">
                      {t("clarificationSubtitle")}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4 space-y-2 text-left">
                    <p className="text-xs uppercase font-semibold text-slate-500">
                      {t("originalAnswerLabel")}
                    </p>
                    <p className="text-base italic text-slate-300">
                      &ldquo;{inputValue}&rdquo;
                    </p>
                  </div>

                  {/* Render fields for each missing attribute requested by the backend */}
                  <div className="space-y-4">
                    {lastAnswer.clarification.missing.map((key) => (
                      <div key={key} className="space-y-1.5 text-left">
                        <label className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
                          {key.replace("_", " ")}
                        </label>
                        {key === "currency" ? (
                          <select
                            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 outline-none transition focus:border-indigo-500"
                            value={clarifyValues[key] || ""}
                            onChange={(e) =>
                              setClarifyValues({
                                ...clarifyValues,
                                [key]: e.target.value,
                              })
                            }
                            required
                          >
                            <option value="" disabled>
                              Select currency...
                            </option>
                            <option value="EUR">EUR (€)</option>
                            <option value="USD">USD ($)</option>
                            <option value="GBP">GBP (£)</option>
                          </select>
                        ) : key === "period" ? (
                          <select
                            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 outline-none transition focus:border-indigo-500"
                            value={clarifyValues[key] || ""}
                            onChange={(e) =>
                              setClarifyValues({
                                ...clarifyValues,
                                [key]: e.target.value,
                              })
                            }
                            required
                          >
                            <option value="" disabled>
                              Select frequency...
                            </option>
                            <option value="monthly">Monthly</option>
                            <option value="yearly">Yearly</option>
                            <option value="weekly">Weekly</option>
                          </select>
                        ) : (
                          <input
                            type="text"
                            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 outline-none transition focus:border-indigo-500"
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
                    ))}
                  </div>

                  <div className="flex gap-4">
                    <button
                      type="button"
                      onClick={handleEditClick}
                      className="flex-1 rounded-xl border border-slate-700 bg-slate-950 py-3.5 text-base font-bold text-slate-300 transition hover:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-700 active:scale-[0.99]"
                    >
                      {tc("edit")}
                    </button>
                    <button
                      type="submit"
                      className="flex-1 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-3.5 text-base font-bold transition hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 active:scale-[0.99]"
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
                    <h2 className="text-xl font-bold text-slate-200">
                      {t("confirmTitle")}
                    </h2>
                  </div>

                  <div className="space-y-4">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4 space-y-2 text-left">
                      <p className="text-xs uppercase font-semibold text-slate-500">
                        {t("originalAnswerLabel")}
                      </p>
                      <p className="text-base italic text-slate-300">
                        &ldquo;{inputValue}&rdquo;
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4 space-y-2 text-left">
                      <p className="text-xs uppercase font-semibold text-indigo-500">
                        {t("proposedValueLabel")}
                      </p>
                      <p className="text-lg font-bold text-indigo-400">
                        {formatProposedValue(
                          lastAnswer.normalizedValue,
                          lastAnswer.outputValue,
                          currentField?.fieldType,
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <button
                      type="button"
                      onClick={handleEditClick}
                      className="flex-1 rounded-xl border border-slate-700 bg-slate-950 py-3.5 text-base font-bold text-slate-300 transition hover:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-700 active:scale-[0.99]"
                    >
                      {tc("edit")}
                    </button>
                    <button
                      type="button"
                      onClick={handleConfirmClick}
                      className="flex-1 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-3.5 text-base font-bold transition hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 active:scale-[0.99]"
                    >
                      {tc("confirm")}
                    </button>
                  </div>
                </div>
              )}

              {/* 3. Primary Answering Flow */}
              {(step === "answering" || step === "submitting") && (
                <form onSubmit={handleSubmitAnswer} className="space-y-6">
                  {/* Dynamic Question Title */}
                  <div className="space-y-1 text-left">
                    <h2 className="text-xl font-bold text-slate-100">
                      {currentField.label}
                      {requiredness === "required" && (
                        <span className="ms-1 text-rose-400" aria-hidden="true">
                          *
                        </span>
                      )}
                    </h2>
                    {/* Only a finding is labelled. When the document carried
                        no marker the backend records "unknown", and saying
                        "Optional" there would claim something the form never
                        said — so nothing is rendered at all. */}
                    {requiredness !== "unknown" && (
                      <p
                        className="text-xs font-medium tracking-wide text-slate-400"
                        data-testid="requiredness"
                      >
                        {requiredness === "required"
                          ? t("required")
                          : t("optional")}
                      </p>
                    )}
                  </div>

                  {/* Render input field */}
                  <FieldRenderer
                    fieldType={currentField.fieldType}
                    fieldKey={currentField.key}
                    required={requiredness === "required"}
                    configuration={{}}
                    options={currentField.options || []}
                    value={inputValue}
                    placeholder={currentField.placeholder || ""}
                    helpText={currentField.helpText || ""}
                    error={
                      errorIsFieldLevel ? errorMsg || undefined : undefined
                    }
                    onChange={(val) => {
                      setErrorMsg(null);
                      setInputValue(val);
                    }}
                  />

                  {/* Footer navigation */}
                  <div className="flex gap-4 pt-4 border-t border-slate-800">
                    <button
                      type="button"
                      disabled={
                        currentField.position === 1 || step === "submitting"
                      }
                      onClick={handleBackClick}
                      className="flex-1 rounded-xl border border-slate-800 bg-slate-950 py-3.5 text-base font-bold text-slate-400 transition hover:border-slate-700 hover:text-slate-300 disabled:opacity-30 disabled:pointer-events-none active:scale-[0.99]"
                    >
                      {tc("back")}
                    </button>
                    {/* Optional *and* unknown can be left unanswered — only a
                        question the form explicitly marked required blocks
                        progress. Unknown does not mean required. */}
                    {requiredness !== "required" && (
                      <button
                        type="button"
                        // Never tied to the input value: skipping is what a
                        // user does *instead* of typing something.
                        disabled={step === "submitting"}
                        onClick={handleSkipClick}
                        data-testid="skip-question"
                        className="flex-1 rounded-xl border border-slate-800 bg-slate-950 py-3.5 text-base font-bold text-slate-400 transition hover:border-slate-700 hover:text-slate-300 disabled:opacity-30 disabled:pointer-events-none active:scale-[0.99]"
                      >
                        {t("skipQuestion")}
                      </button>
                    )}
                    <button
                      type="submit"
                      disabled={!inputValue.trim() || step === "submitting"}
                      className="flex-1 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-3.5 text-base font-bold transition hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 disabled:opacity-40 disabled:pointer-events-none active:scale-[0.99]"
                    >
                      {step === "submitting" ? tc("loading") : tc("continue")}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
