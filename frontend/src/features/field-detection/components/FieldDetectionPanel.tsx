"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  createSessionFromFieldDetection,
  getFieldDetectionResult,
  rejectDetectedField,
  requestFieldDetection,
  updateDetectedField,
} from "../services/apiClient";
import { setSessionToken } from "../../form-session/services/sessionCredentials";
import { ApiError } from "../../form-session/services/apiClient";
import { DetectedField, FIELD_TYPES, FieldDetectionResultResponse, LOW_CONFIDENCE_THRESHOLD } from "../types";

interface FieldDetectionPanelProps {
  documentId: string;
  currentLocale: string;
}

type Stage = "idle" | "processing" | "reviewing" | "creating_session" | "failed";

export default function FieldDetectionPanel({
  documentId,
  currentLocale,
}: FieldDetectionPanelProps) {
  const router = useRouter();
  const t = useTranslations("fieldDetection");

  const [stage, setStage] = useState<Stage>("idle");
  const [result, setResult] = useState<FieldDetectionResultResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [outputLanguage, setOutputLanguage] = useState<string>(currentLocale);
  const [creatingSession, setCreatingSession] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadExisting() {
      try {
        const existing = await getFieldDetectionResult(documentId);
        if (cancelled) return;
        setResult(existing);
        setStage(existing.status === "completed" ? "reviewing" : "idle");
      } catch {
        // No prior detection result yet; stay idle.
      }
    }

    loadExisting();
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  const mapApiError = (err: unknown): string => {
    if (err instanceof ApiError) {
      const key = `error_${err.detail}`;
      const msg = t(key);
      return msg && msg !== key ? msg : err.message || t("error_generic");
    }
    return t("error_generic");
  };

  const handleStartDetection = async () => {
    setStage("processing");
    setErrorMsg(null);
    try {
      const response = await requestFieldDetection(documentId);
      setResult(response);
      setStage(response.status === "completed" ? "reviewing" : "failed");
    } catch (err) {
      setStage("failed");
      setErrorMsg(mapApiError(err));
    }
  };

  const updateLocalField = (updated: DetectedField) => {
    setResult((prev) =>
      prev
        ? {
            ...prev,
            fields: prev.fields.map((f) => (f.fieldId === updated.fieldId ? updated : f)),
          }
        : prev
    );
  };

  const handleConfirm = async (fieldId: string) => {
    try {
      const updated = await updateDetectedField(documentId, fieldId, {
        reviewStatus: "confirmed",
      });
      updateLocalField(updated);
    } catch (err) {
      setErrorMsg(mapApiError(err));
    }
  };

  const handleReject = async (fieldId: string) => {
    try {
      const updated = await rejectDetectedField(documentId, fieldId);
      updateLocalField(updated);
    } catch (err) {
      setErrorMsg(mapApiError(err));
    }
  };

  const handleLabelChange = async (fieldId: string, label: string) => {
    try {
      const updated = await updateDetectedField(documentId, fieldId, { label });
      updateLocalField(updated);
    } catch (err) {
      setErrorMsg(mapApiError(err));
    }
  };

  const handleTypeChange = async (fieldId: string, fieldType: string) => {
    try {
      const updated = await updateDetectedField(documentId, fieldId, { fieldType });
      updateLocalField(updated);
    } catch (err) {
      setErrorMsg(mapApiError(err));
    }
  };

  const handleConfirmAllHighConfidence = async () => {
    if (!result) return;
    const candidates = result.fields.filter(
      (f) => f.reviewStatus === "pending_review" && f.confidence >= LOW_CONFIDENCE_THRESHOLD
    );
    for (const field of candidates) {
      // eslint-disable-next-line no-await-in-loop
      await handleConfirm(field.fieldId);
    }
  };

  const confirmedCount = useMemo(
    () => (result ? result.fields.filter((f) => f.reviewStatus === "confirmed").length : 0),
    [result]
  );

  const handleCreateQuestions = async () => {
    setCreatingSession(true);
    setErrorMsg(null);
    try {
      const session = await createSessionFromFieldDetection(
        documentId,
        currentLocale,
        outputLanguage
      );
      setSessionToken(session.sessionId, session.ownershipToken);
      router.push(`/application/session/${session.sessionId}`);
    } catch (err) {
      setCreatingSession(false);
      setErrorMsg(mapApiError(err));
    }
  };

  const fieldsByPage = useMemo(() => {
    if (!result) return [];
    const groups = new Map<number, DetectedField[]>();
    for (const field of result.fields) {
      const existing = groups.get(field.pageNumber) || [];
      existing.push(field);
      groups.set(field.pageNumber, existing);
    }
    return Array.from(groups.entries()).sort(([a], [b]) => a - b);
  }, [result]);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-6 space-y-4">
        <h2 className="text-xl font-bold text-slate-200">{t("title")}</h2>
        <p className="text-xs leading-relaxed text-slate-400">{t("body")}</p>

        {stage === "idle" && (
          <button
            type="button"
            onClick={handleStartDetection}
            className="w-full rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-3.5 text-sm font-bold shadow-lg shadow-indigo-500/20 transition hover:opacity-95"
          >
            {t("startDetection")}
          </button>
        )}

        {stage === "processing" && (
          <div className="flex items-center justify-center gap-2 py-4">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
            <span className="text-sm text-slate-400">{t("processing")}</span>
          </div>
        )}

        {stage === "failed" && errorMsg && (
          <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300">
            {errorMsg}
          </div>
        )}
      </div>

      {stage === "reviewing" && result && (
        <div className="space-y-4">
          <p className="text-xs italic text-slate-400 px-1">{t("disclaimer")}</p>

          <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-6 space-y-3">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span>{t("fieldCount", { count: result.fieldCount ?? result.fields.length })}</span>
              <span>{t("confirmedCount", { count: confirmedCount })}</span>
            </div>
            <button
              type="button"
              onClick={handleConfirmAllHighConfidence}
              className="w-full rounded-lg bg-slate-800 py-2.5 text-xs font-semibold text-slate-200 hover:bg-slate-700"
            >
              {t("confirmAllHighConfidence")}
            </button>
          </div>

          {fieldsByPage.map(([pageNumber, fields]) => (
            <div
              key={pageNumber}
              className="rounded-2xl border border-slate-800 bg-slate-950/40 p-6 space-y-3"
            >
              <h3 className="text-sm font-bold text-slate-300">
                {t("page", { number: pageNumber })}
              </h3>
              {fields.map((field) => (
                <div
                  key={field.fieldId}
                  className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <input
                      dir="auto"
                      value={field.label}
                      onChange={(e) =>
                        updateLocalField({ ...field, label: e.target.value })
                      }
                      onBlur={(e) => handleLabelChange(field.fieldId, e.target.value)}
                      className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-indigo-500"
                      disabled={field.reviewStatus === "rejected"}
                    />
                    <select
                      value={field.fieldType}
                      onChange={(e) => handleTypeChange(field.fieldId, e.target.value)}
                      className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-2 text-xs text-slate-100 outline-none focus:border-indigo-500"
                      disabled={field.reviewStatus === "rejected"}
                    >
                      {FIELD_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {t(`type_${type}`)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <span
                      className={
                        field.confidence < LOW_CONFIDENCE_THRESHOLD
                          ? "text-amber-400 font-semibold"
                          : "text-slate-500"
                      }
                    >
                      {t("confidence", { value: Math.round(field.confidence * 100) })}
                      {field.confidence < LOW_CONFIDENCE_THRESHOLD && (
                        <span className="ml-1">{t("lowConfidenceWarning")}</span>
                      )}
                    </span>
                    <span className="rounded-full bg-slate-800 px-2 py-0.5 text-slate-400">
                      {t(`status_${field.reviewStatus}`)}
                    </span>
                  </div>

                  <div className="flex gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => handleConfirm(field.fieldId)}
                      disabled={field.reviewStatus === "confirmed"}
                      className="flex-1 rounded-lg bg-emerald-600/20 py-2 text-xs font-semibold text-emerald-300 hover:bg-emerald-600/30 disabled:opacity-40"
                    >
                      {t("confirmField")}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleReject(field.fieldId)}
                      disabled={field.reviewStatus === "rejected"}
                      className="flex-1 rounded-lg bg-rose-600/20 py-2 text-xs font-semibold text-rose-300 hover:bg-rose-600/30 disabled:opacity-40"
                    >
                      {t("rejectField")}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ))}

          <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-6 space-y-4">
            <div className="space-y-2">
              <label
                htmlFor="output-language-select"
                className="block text-sm font-semibold tracking-wide text-slate-300"
              >
                {t("selectOutputLanguage")}
              </label>
              <select
                id="output-language-select"
                value={outputLanguage}
                onChange={(e) => setOutputLanguage(e.target.value)}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3.5 text-base text-slate-100 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 cursor-pointer"
              >
                <option value="en">English</option>
                <option value="de">Deutsch</option>
                <option value="fr">Français</option>
                <option value="ar">العربية</option>
              </select>
            </div>

            {errorMsg && (
              <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300">
                {errorMsg}
              </div>
            )}

            <button
              type="button"
              disabled={confirmedCount === 0 || creatingSession}
              onClick={handleCreateQuestions}
              className="w-full rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-3.5 text-sm font-bold shadow-lg shadow-indigo-500/20 transition hover:opacity-95 disabled:opacity-40 disabled:pointer-events-none"
            >
              {creatingSession ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                  <span>{t("processing")}</span>
                </div>
              ) : (
                <span>{t("createQuestions")}</span>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
