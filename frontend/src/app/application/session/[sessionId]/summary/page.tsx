"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  getSummary,
  confirmSummary,
  reopenField,
  fetchWatermarkedPreviewPdfBlob,
  ApiError,
  Summary,
} from "@/features/form-session/services/apiClient";
import { removeSessionToken } from "@/features/form-session/services/sessionCredentials";
import {
  parseRowKey,
  rowHeading,
} from "@/features/form-session/utils/repeatedRows";
import {
  formatOriginalAnswer,
  formatProposedValue,
} from "@/features/form-session/utils/formatProposedValue";
import { formatFieldLabel } from "@/features/form-session/utils/formatFieldLabel";

export default function SessionSummary() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const t = useTranslations("summary");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const ts = useTranslations("signature");

  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [blockingFields, setBlockingFields] = useState<Map<string, string>>(
    new Map(),
  );

  useEffect(() => {
    async function loadSummary() {
      try {
        setLoading(true);
        setErrorMsg(null);
        const data = await getSummary(sessionId);
        setSummary(data);
      } catch (err: any) {
        setErrorMsg(
          te(err.message) || "Failed to load session summary details.",
        );
      } finally {
        setLoading(false);
      }
    }
    loadSummary();
  }, [sessionId, te]);

  const handleEditField = async (fieldId: string) => {
    try {
      setLoading(true);
      setErrorMsg(null);

      await reopenField(sessionId, fieldId);

      router.push(`/application/session/${sessionId}`);
    } catch (err: any) {
      setErrorMsg(te(err.message) || "Failed to initiate field edit.");
      setLoading(false);
    }
  };

  const handleConfirmSummary = async () => {
    if (submitting) return;

    try {
      setSubmitting(true);
      setErrorMsg(null);

      await confirmSummary(sessionId);

      router.push(`/application/session/${sessionId}/complete`);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 409) {
        const blocking = [
          ...err.missingRequiredFields,
          ...err.invalidAnswerFields,
        ];
        if (blocking.length > 0) {
          setBlockingFields(
            new Map(blocking.map((p) => [p.fieldKey, p.reason])),
          );
          setErrorMsg(t("blockedByFields", { count: blocking.length }));
          setSubmitting(false);
          return;
        }
      }
      setErrorMsg(
        te(err.message) || "Failed to finalize summary confirmation.",
      );
      setSubmitting(false);
    }
  };

  const handleRestart = () => {
    removeSessionToken(sessionId);
    router.push("/application");
  };

  const handlePreviewPdf = async () => {
    if (previewLoading) return;
    try {
      setPreviewLoading(true);
      setErrorMsg(null);
      const blob = await fetchWatermarkedPreviewPdfBlob(sessionId);
      const objectUrl = URL.createObjectURL(blob);
      window.open(objectUrl, "_blank", "noopener,noreferrer");
      setTimeout(() => {
        try {
          URL.revokeObjectURL(objectUrl);
        } catch {
          // ignore cleanup failure
        }
      }, 60_000);
    } catch (err: unknown) {
      const code = err instanceof Error ? err.message : "unavailable";
      setErrorMsg(te(code) || t("previewPdfError"));
    } finally {
      setPreviewLoading(false);
    }
  };

  if (loading) {
    return (
      <main className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center text-slate-900">
        <div className="flex flex-col items-center gap-3">
          <div className="h-9 w-9 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600" />
          <p className="text-sm font-medium text-slate-600">{tc("loading")}</p>
        </div>
      </main>
    );
  }

  type RowState =
    | "confirmed"
    | "pendingManualSignature"
    | "skipped"
    | "notAnswered"
    | "missingRequired"
    | "invalid"
    | "pending";

  const rowState = (f: Summary["fields"][number]): RowState => {
    const requiredness =
      f.requiredness ?? (f.required ? "required" : "unknown");
    const state = f.answerState ?? (f.status === "skipped" ? "skipped" : null);

    if (state === "pending_manual_signature") return "pendingManualSignature";
    if (state === "skipped") return "skipped";
    if (state === "invalid") return "invalid";
    if (f.status === "confirmed") return "confirmed";
    if (requiredness === "required") return "missingRequired";
    if (state === "unreached" || state === "unanswered" || !f.originalAnswer) {
      return "notAnswered";
    }
    return "pending";
  };

  const hasIncompleteFields = summary?.fields.some((f) => {
    const state = rowState(f);
    return state === "missingRequired" || state === "invalid";
  });

  const renderField = (f: Summary["fields"][number]) => {
    const state = rowState(f);
    const blocks =
      state === "missingRequired" ||
      state === "invalid" ||
      blockingFields.has(f.fieldKey);
    const isRequired =
      (f.requiredness ??
        (f.required ? "required" : "unknown")) === "required";

    return (
      <tr
        key={f.fieldId}
        data-testid={`summary-row-${f.fieldKey}`}
        data-state={state}
        className={`transition-colors duration-150 ${
          blocks ? "bg-rose-50" : "hover:bg-slate-50"
        }`}
      >
        <td className="px-4 py-3.5 font-semibold text-slate-900">
          {formatFieldLabel(f.label)}
          {isRequired && (
            <span className="text-rose-600 ms-1">*</span>
          )}
        </td>
        <td className="px-4 py-3.5 text-slate-600 max-w-xs break-words">
          {formatOriginalAnswer(f.originalAnswer, f.fieldType) ||
            (f.fieldType === "signature" && state === "confirmed"
              ? "Hand-drawn signature"
              : "-")}
        </td>
        <td className="px-4 py-3.5 text-slate-900 font-semibold break-words">
          {formatProposedValue(
            f.normalizedValue,
            f.outputValue,
            f.fieldType
          ) || "-"}
        </td>
        <td className="px-4 py-3.5">
          <span
            data-testid={`summary-status-${f.fieldKey}`}
            className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
              state === "confirmed"
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : blocks
                  ? "border-rose-200 bg-rose-50 text-rose-700"
                  : "border-slate-200 bg-slate-100 text-slate-700"
            }`}
          >
            {state === "pendingManualSignature"
              ? ts("summaryPending")
              : state === "skipped"
              ? t("skipped")
              : state === "notAnswered"
                ? t("notAnswered")
                : state === "missingRequired"
                  ? t("missingRequired")
                  : state === "invalid"
                    ? t("invalidAnswer")
                    : f.status}
          </span>
        </td>
        <td className="px-4 py-3.5 text-end">
          <button
            type="button"
            onClick={() => handleEditField(f.fieldId)}
            className="rounded-md px-2.5 py-1 text-xs font-semibold text-indigo-600 hover:bg-indigo-50 hover:text-indigo-800 transition-colors"
          >
            {tc("edit")}
          </button>
        </td>
      </tr>
    );
  };

  type SummaryEntry =
    | { kind: "heading"; id: string; label: string }
    | { kind: "field"; field: Summary["fields"][number] };

  const rowsWithHeadings: SummaryEntry[] = [];
  let openRow: string | null = null;
  for (const field of summary?.fields ?? []) {
    const parts = parseRowKey(field.fieldKey);
    const rowId = parts ? `${parts.section}-${parts.index}` : null;
    if (rowId && rowId !== openRow) {
      rowsWithHeadings.push({
        kind: "heading",
        id: rowId,
        label: rowHeading(parts!.section, parts!.index),
      });
    }
    openRow = rowId;
    rowsWithHeadings.push({ kind: "field", field });
  }

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col justify-center px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-5xl">
        <div className="surface-panel rounded-2xl p-6 sm:p-10 space-y-6">
          <div className="space-y-1 text-center">
            <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
              <span className="tabular-nums">Step 3 of 4 • Final Review</span>
            </div>
            <h1 className="mt-3 text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
              {t("title")}
            </h1>
            <p className="text-sm text-slate-600">{t("subtitle")}</p>
          </div>

          {/* Quick Metrics Bar */}
          {summary && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Total Form Fields
                </span>
                <p className="mt-1 text-2xl font-bold text-slate-900 tabular-nums">
                  {summary.fields.length}
                </p>
              </div>
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 text-center">
                <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-700">
                  Confirmed Answers
                </span>
                <p className="mt-1 text-2xl font-bold text-emerald-800 tabular-nums">
                  {summary.fields.filter((f) => f.status === "confirmed").length}
                </p>
              </div>
              <div className="col-span-2 sm:col-span-1 rounded-xl border border-indigo-200 bg-indigo-50/70 p-4 text-center">
                <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">
                  Export Status
                </span>
                <p className="mt-1 text-sm font-bold text-indigo-900 flex items-center justify-center gap-1.5 pt-1">
                  <span className="h-2 w-2 rounded-full bg-emerald-600" />
                  {!hasIncompleteFields ? "Ready for Export" : "Incomplete Fields"}
                </p>
              </div>
            </div>
          )}

          {errorMsg && (
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

          {/* Fields table summary */}
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="overflow-x-auto">
              <table className="w-full text-start border-collapse text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-600">
                    <th className="px-4 py-3.5 text-start">{t("fieldHeader")}</th>
                    <th className="px-4 py-3.5 text-start">{t("originalHeader")}</th>
                    <th className="px-4 py-3.5 text-start">{t("normalizedHeader")}</th>
                    <th className="px-4 py-3.5 text-start">{t("statusHeader")}</th>
                    <th className="px-4 py-3.5 text-end">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {rowsWithHeadings.map((entry) =>
                    entry.kind === "heading" ? (
                      <tr
                        key={`heading-${entry.id}`}
                        data-testid={`row-heading-${entry.id}`}
                        className="bg-indigo-50/70 border-t border-b border-indigo-200"
                      >
                        <td
                          colSpan={5}
                          className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-indigo-800"
                        >
                          {entry.label}
                        </td>
                      </tr>
                    ) : (
                      renderField(entry.field)
                    ),
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Warning block */}
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-relaxed text-amber-900 text-start flex items-start gap-3">
            <svg className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{t("warning")}</span>
          </div>

          {/* Confirm button / Preview PDF / Restart button */}
          <div className="flex flex-col gap-3 pt-2">
            <button
              type="button"
              disabled={hasIncompleteFields || submitting}
              onClick={handleConfirmSummary}
              className="btn-primary w-full py-3.5 text-sm font-semibold"
            >
              {submitting ? tc("loading") : t("submitSummary")}
            </button>
            <button
              type="button"
              disabled={previewLoading || submitting}
              onClick={handlePreviewPdf}
              className="btn-secondary w-full py-3 text-sm font-semibold"
            >
              {previewLoading ? t("previewPdfLoading") : t("previewPdf")}
            </button>
            <button
              type="button"
              onClick={handleRestart}
              className="btn-secondary w-full py-3 text-sm font-medium"
            >
              {tc("restart")}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
