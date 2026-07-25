"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  startSession,
  getCurrentField,
  submitAnswer,
  submitClarification,
  confirmAnswer,
  previousField,
  changeAnswer,
  getSummary,
  CurrentField,
  AnswerResponse,
} from "@/features/form-session/services/apiClient";
import { getSessionToken, removeSessionToken } from "@/features/form-session/services/sessionCredentials";
import { FieldRenderer } from "@/features/form-session/components/FieldRenderer";

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
  const [currentField, setCurrentFieldData] = useState<CurrentField | null>(null);
  const [inputValue, setInputValue] = useState<string>("");
  const [lastAnswer, setLastAnswer] = useState<AnswerResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Clarification form state
  const [clarifyValues, setClarifyValues] = useState<Record<string, any>>({});

  const fetchNextQuestion = useCallback(async () => {
    try {
      setErrorMsg(null);
      const field = await getCurrentField(sessionId);
      console.log("FETCHED FIELD:", field.label, "KEY:", field.key, "STATUS:", field.currentAnswerStatus);
      setCurrentFieldData(field);

      // Check if session is fully complete (all required questions confirmed)
      const total = field.progress?.totalRequiredFields || 0;
      const completed = field.progress?.confirmedRequiredFields || 0;
      if (total > 0 && completed === total) {
        // Automatically direct user to the summary screen
        router.push(`/application/session/${sessionId}/summary`);
        return;
      }

      // Populate input value if there is an existing answer in summary
      if (field.currentAnswerStatus) {
        try {
          const summary = await getSummary(sessionId);
          const answerInfo = summary.fields.find((f: any) => f.fieldId === field.fieldId);
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
    // Check credentials first
    const token = getSessionToken(sessionId);
    if (!token) {
      setErrorMsg(te("unauthorized"));
      setStep("error");
      return;
    }

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
        setErrorMsg(te(err.message) || "Failed to initialize assisted session. Please retry.");
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

      console.log("SUBMITTING ANSWER FOR FIELD:", currentField.fieldId, "VALUE:", inputValue);
      const response = await submitAnswer(sessionId, currentField.fieldId, inputValue);
      console.log("SUBMIT ANSWER RESPONSE STATUS:", response.status, "ID:", response.id);
      setLastAnswer(response);

      handleAnswerTransitions(response);
    } catch (err: any) {
      console.error("SUBMIT ANSWER ERROR:", err.message, err.detail);
      setErrorMsg(te(err.message) || "Failed to submit answer. Please try again.");
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

      const response = await submitClarification(sessionId, lastAnswer.id, clarifyValues);
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
      setStep("awaiting_confirmation");
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
          const answerInfo = summary.fields.find((f: any) => f.fieldId === prev.fieldId);
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

  // Progress percentage calculation
  const total = currentField?.progress?.totalRequiredFields || 0;
  const completed = currentField?.progress?.confirmedRequiredFields || 0;
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
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-slate-200">Error Occurred</h2>
          <p className="mt-2 text-sm text-slate-400">{errorMsg || "An unexpected error occurred."}</p>
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
        {/* Progress header */}
        {currentField && (
          <div className="mb-6 w-full space-y-2">
            <div className="flex justify-between text-xs font-semibold tracking-wide text-slate-400">
              <span>{t("progress", { current: completed + 1, total, percent: progressPercent })}</span>
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
              {errorMsg && (
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
                            onChange={(e) => setClarifyValues({ ...clarifyValues, [key]: e.target.value })}
                            required
                          >
                            <option value="" disabled>Select currency...</option>
                            <option value="EUR">EUR (€)</option>
                            <option value="USD">USD ($)</option>
                            <option value="GBP">GBP (£)</option>
                          </select>
                        ) : key === "period" ? (
                          <select
                            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 outline-none transition focus:border-indigo-500"
                            value={clarifyValues[key] || ""}
                            onChange={(e) => setClarifyValues({ ...clarifyValues, [key]: e.target.value })}
                            required
                          >
                            <option value="" disabled>Select frequency...</option>
                            <option value="monthly">Monthly</option>
                            <option value="yearly">Yearly</option>
                            <option value="weekly">Weekly</option>
                          </select>
                        ) : (
                          <input
                            type="text"
                            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 outline-none transition focus:border-indigo-500"
                            value={clarifyValues[key] || ""}
                            onChange={(e) => setClarifyValues({ ...clarifyValues, [key]: e.target.value })}
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
                        {lastAnswer.outputValue || JSON.stringify(lastAnswer.normalizedValue)}
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
                    </h2>
                  </div>

                  {/* Render input field */}
                  <FieldRenderer
                    fieldType={currentField.fieldType}
                    fieldKey={currentField.key}
                    required={currentField.required}
                    configuration={{}}
                    options={currentField.options || []}
                    value={inputValue}
                    placeholder={currentField.placeholder || ""}
                    helpText={currentField.helpText || ""}
                    error={errorMsg || undefined}
                    onChange={(val) => {
                      setErrorMsg(null);
                      setInputValue(val);
                    }}
                  />

                  {/* Footer navigation */}
                  <div className="flex gap-4 pt-4 border-t border-slate-800">
                    <button
                      type="button"
                      disabled={currentField.position === 1 || step === "submitting"}
                      onClick={handleBackClick}
                      className="flex-1 rounded-xl border border-slate-800 bg-slate-950 py-3.5 text-base font-bold text-slate-400 transition hover:border-slate-700 hover:text-slate-300 disabled:opacity-30 disabled:pointer-events-none active:scale-[0.99]"
                    >
                      {tc("back")}
                    </button>
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
