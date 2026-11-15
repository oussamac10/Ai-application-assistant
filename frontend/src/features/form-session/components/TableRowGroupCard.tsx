"use client";

import React, { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  CircleDot,
  FastForward,
  Loader2,
  SkipForward,
  Table2,
} from "lucide-react";
import {
  TableRowContext,
  skipTableRow,
  submitTableRow,
} from "../services/apiClient";
import { FieldRenderer } from "./FieldRenderer";

interface TableRowGroupCardProps {
  sessionId: string;
  tableRow: TableRowContext;
  onRowCompleted: () => Promise<void>;
  onSelectRow?: (firstFieldId: string) => Promise<void>;
  onSwitchToSingleField: () => void;
  onNeedsClarification?: (fieldId: string) => Promise<void>;
}

const KNOWN_REASON_KEYS = new Set([
  "missing_required",
  "invalid_date",
  "invalid_country",
  "invalid_email",
  "invalid_phone",
  "invalid_number",
  "invalid_currency",
  "invalid_choice",
  "invalid_iban",
  "needs_clarification",
  "invalid_value",
]);

export function TableRowGroupCard({
  sessionId,
  tableRow,
  onRowCompleted,
  onSelectRow,
  onSwitchToSingleField,
  onNeedsClarification,
}: TableRowGroupCardProps) {
  const t = useTranslations("workflow");
  const [values, setValues] = useState<Record<string, string>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [errorSummaryLabels, setErrorSummaryLabels] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const keyFor = (field: { fieldId?: string; fieldKey: string }) =>
    field.fieldId || field.fieldKey;

  useEffect(() => {
    const initial: Record<string, string> = {};
    for (const f of tableRow.fields) {
      initial[f.fieldId || f.fieldKey] = f.originalAnswer ?? "";
    }
    setValues(initial);
    setFieldErrors({});
    setErrorSummaryLabels([]);
    setGlobalError(null);
  }, [tableRow]);

  const resolveReason = (reasonCode?: string): string => {
    const code =
      reasonCode && KNOWN_REASON_KEYS.has(reasonCode)
        ? reasonCode
        : "invalid_value";
    return t(`reason_${code}` as Parameters<typeof t>[0]);
  };

  const allOptionalOrUnknown = tableRow.fields.every(
    (f) => !f.required && f.requiredness !== "required",
  );
  const rowsOverview = tableRow.rowsOverview || [];
  const hasRemainingEmptyRows =
    tableRow.rowIndex < tableRow.totalRows ||
    rowsOverview.some(
      (r) =>
        r.rowIndex > tableRow.rowIndex &&
        r.status !== "completed" &&
        r.status !== "skipped",
    );

  const handleSaveRow = async () => {
    setGlobalError(null);
    setErrorSummaryLabels([]);
    const localErrors: Record<string, string> = {};
    const localBadLabels: string[] = [];

    for (const f of tableRow.fields) {
      const k = keyFor(f);
      const val = (values[k] ?? "").trim();
      if ((f.required || f.requiredness === "required") && !val) {
        localErrors[k] = resolveReason("missing_required");
        localBadLabels.push(f.label);
      }
    }

    if (Object.keys(localErrors).length > 0) {
      setFieldErrors(localErrors);
      setErrorSummaryLabels(localBadLabels);
      return;
    }

    setSubmitting(true);
    try {
      const items = tableRow.fields.map((f) => ({
        fieldId: f.fieldId || f.fieldKey,
        value: (values[keyFor(f)] ?? "").trim(),
      }));
      const res = await submitTableRow(sessionId, items);

      if (res.status === "validation_error") {
        const mappedErrors: Record<string, string> = {};
        const labels: string[] = [];
        for (const err of res.fieldErrors) {
          const targetKey = err.fieldId || err.fieldKey;
          mappedErrors[targetKey] = resolveReason(err.reasonCode);
          if (err.label) labels.push(err.label);
        }
        setFieldErrors(mappedErrors);
        setErrorSummaryLabels(labels);
        return;
      }

      if (res.status === "needs_clarification") {
        const firstClarifyId = res.clarificationFieldIds[0];
        if (firstClarifyId && onNeedsClarification) {
          await onNeedsClarification(firstClarifyId);
          return;
        }
        const clarErrors: Record<string, string> = {};
        for (const fid of res.clarificationFieldIds) {
          clarErrors[fid] = resolveReason("needs_clarification");
        }
        setFieldErrors(clarErrors);
        return;
      }

      await onRowCompleted();
    } catch (err) {
      const rawMsg =
        err instanceof Error && err.message && err.message !== "validation"
          ? err.message
          : resolveReason("invalid_value");
      setGlobalError(rawMsg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSkipRow = async (skipRemainingEmptyRows = false) => {
    setSubmitting(true);
    setGlobalError(null);
    setErrorSummaryLabels([]);
    try {
      const fieldIds = tableRow.fields.map((f) => f.fieldId || f.fieldKey);
      const res = await skipTableRow(sessionId, {
        fieldIds,
        skipRemainingEmptyRows,
        tableKey: skipRemainingEmptyRows ? tableRow.tableKey : undefined,
        fromRowIndex: skipRemainingEmptyRows ? tableRow.rowIndex : undefined,
      });

      if (res.status === "validation_error") {
        const mappedErrors: Record<string, string> = {};
        const labels: string[] = [];
        for (const err of res.fieldErrors) {
          mappedErrors[err.fieldId || err.fieldKey] = resolveReason(
            err.reasonCode,
          );
          if (err.label) labels.push(err.label);
        }
        setFieldErrors(mappedErrors);
        setErrorSummaryLabels(labels);
        return;
      }

      await onRowCompleted();
    } catch (err) {
      setGlobalError(
        err instanceof Error && err.message !== "validation"
          ? err.message
          : resolveReason("invalid_value"),
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="table-row-group-card">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] pb-3.5">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 shrink-0">
            <Table2 className="h-4 w-4" />
          </div>
          <div className="min-w-0 text-start">
            <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 leading-snug">
              {tableRow.tableTitle}
            </p>
            <div className="flex flex-wrap items-center gap-2 mt-0.5">
              <h2 className="text-base sm:text-lg font-bold text-[var(--text-primary)]">
                {t("tableRowCount", {
                  current: tableRow.rowIndex,
                  total: tableRow.totalRows,
                })}
              </h2>
              {tableRow.rowLabel && (
                <span className="inline-flex items-center rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
                  {tableRow.rowLabel}
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onSwitchToSingleField}
          className="text-xs font-medium text-[var(--text-secondary)] hover:text-emerald-600 dark:hover:text-emerald-400 underline underline-offset-2 cursor-pointer shrink-0"
        >
          {t("fillOneByOne")}
        </button>
      </div>

      {/* Clickable row selector pills */}
      {rowsOverview.length > 1 && (
        <div
          className="flex flex-wrap gap-1.5"
          role="tablist"
          aria-label={tableRow.tableTitle}
        >
          {rowsOverview.map((row) => {
            const isCurrent = row.rowIndex === tableRow.rowIndex;
            const isDone = row.status === "completed";
            const isSkipped = row.status === "skipped";
            return (
              <button
                key={row.rowIndex}
                type="button"
                role="tab"
                aria-selected={isCurrent}
                disabled={submitting || !onSelectRow}
                onClick={() => onSelectRow?.(row.firstFieldId)}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-all cursor-pointer disabled:opacity-60 ${
                  isCurrent
                    ? "border-emerald-500 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 ring-1 ring-emerald-500/30"
                    : isDone
                      ? "border-emerald-500/30 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/10"
                      : "border-[var(--border-subtle)] bg-[var(--bg-muted)] text-[var(--text-secondary)] hover:border-emerald-500/40 hover:text-[var(--text-primary)]"
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                ) : isSkipped ? (
                  <FastForward className="h-3.5 w-3.5 text-[var(--text-muted)] shrink-0" />
                ) : isCurrent ? (
                  <CircleDot className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                ) : (
                  <Circle className="h-3.5 w-3.5 text-[var(--text-muted)] shrink-0" />
                )}
                <span>
                  {row.rowLabel ||
                    t("tableRowTab", { index: row.rowIndex })}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {tableRow.tableDescription && (
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-muted)] px-3.5 py-2.5 text-xs text-[var(--text-secondary)] leading-relaxed text-start">
          {tableRow.tableDescription}
        </div>
      )}

      {(globalError || errorSummaryLabels.length > 0) && (
        <div
          role="alert"
          className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-xs font-medium text-rose-700 dark:text-rose-200 text-start flex items-start gap-2.5"
        >
          <AlertCircle className="h-4 w-4 text-rose-500 dark:text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <p className="font-semibold">
              {globalError || t("tableRowCheckHighlighted")}
            </p>
            {errorSummaryLabels.length > 0 && (
              <p className="text-[11px] opacity-90">
                {errorSummaryLabels.join(" · ")}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Row fields */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {tableRow.fields.map((f) => {
          const k = keyFor(f);
          const errMsg = fieldErrors[k];
          return (
            <div
              key={k}
              className={`rounded-xl border p-3.5 space-y-2 text-start transition-colors ${
                errMsg
                  ? "border-rose-500/60 bg-rose-500/[0.04] ring-1 ring-rose-500/30"
                  : "border-[var(--border-subtle)] bg-[var(--bg-muted)]"
              }`}
            >
              <label
                htmlFor={`field-${f.fieldKey}`}
                className="block text-xs font-semibold text-[var(--text-primary)]"
              >
                {f.label}
                {(f.required || f.requiredness === "required") && (
                  <span className="ms-1 text-rose-500" aria-hidden="true">
                    *
                  </span>
                )}
              </label>
              <FieldRenderer
                fieldType={f.fieldType}
                fieldKey={f.fieldKey}
                required={f.required || f.requiredness === "required"}
                configuration={{}}
                options={f.options || []}
                value={values[k] ?? ""}
                placeholder={f.placeholder || ""}
                error={errMsg}
                enableVoiceInput={false}
                compactChoicePills={true}
                onChange={(val) => {
                  setFieldErrors((prev) => {
                    const next = { ...prev };
                    delete next[k];
                    return next;
                  });
                  setValues((prev) => ({ ...prev, [k]: val }));
                }}
              />
            </div>
          );
        })}
      </div>

      {/* Footer actions */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 pt-2 border-t border-[var(--border-subtle)]">
        <div className="flex flex-wrap items-center gap-2">
          {allOptionalOrUnknown && (
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleSkipRow(false)}
              className="btn-secondary inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold"
            >
              <SkipForward className="h-3.5 w-3.5" />
              <span>{t("skipRow")}</span>
            </button>
          )}
          {allOptionalOrUnknown && hasRemainingEmptyRows && (
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleSkipRow(true)}
              className="btn-secondary inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold"
            >
              <FastForward className="h-3.5 w-3.5" />
              <span>{t("skipRemainingEmptyRows")}</span>
            </button>
          )}
        </div>

        <button
          type="button"
          disabled={submitting}
          onClick={handleSaveRow}
          className="btn-primary inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold disabled:opacity-50 cursor-pointer"
        >
          {submitting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <CheckCircle2 className="h-4 w-4" />
          )}
          <span>{t("saveRowContinue")}</span>
        </button>
      </div>
    </div>
  );
}
