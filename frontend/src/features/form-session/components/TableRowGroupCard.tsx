"use client";

import React, { useEffect, useState } from "react";
import { Loader2, Table2, CheckCircle2, SkipForward } from "lucide-react";
import {
  TableRowContext,
  submitAnswer,
  confirmAnswer,
  skipField,
} from "../services/apiClient";
import { FieldRenderer } from "./FieldRenderer";

interface TableRowGroupCardProps {
  sessionId: string;
  tableRow: TableRowContext;
  onRowCompleted: () => Promise<void>;
  onSwitchToSingleField: () => void;
}

export function TableRowGroupCard({
  sessionId,
  tableRow,
  onRowCompleted,
  onSwitchToSingleField,
}: TableRowGroupCardProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  useEffect(() => {
    const initial: Record<string, string> = {};
    for (const f of tableRow.fields) {
      initial[f.fieldKey] = f.originalAnswer ?? "";
    }
    setValues(initial);
    setFieldErrors({});
    setGlobalError(null);
  }, [tableRow]);

  const allOptionalOrUnknown = tableRow.fields.every(
    (f) => !f.required && f.requiredness !== "required",
  );

  const handleSaveRow = async () => {
    setGlobalError(null);
    const errors: Record<string, string> = {};
    for (const f of tableRow.fields) {
      const val = (values[f.fieldKey] ?? "").trim();
      if ((f.required || f.requiredness === "required") && !val) {
        errors[f.fieldKey] = "This field is required.";
      }
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setSubmitting(true);
    try {
      for (const f of tableRow.fields) {
        const val = (values[f.fieldKey] ?? "").trim();
        if (!val) {
          if (f.currentAnswerStatus !== "confirmed" && f.currentAnswerStatus !== "skipped") {
            await skipField(sessionId, f.fieldKey);
          }
          continue;
        }
        const res = await submitAnswer(sessionId, f.fieldKey, val);
        if (res.status === "awaiting_confirmation" && res.id) {
          await confirmAnswer(sessionId, res.id);
        } else if (res.status === "invalid" || res.status === "needs_clarification") {
          setFieldErrors((prev) => ({
            ...prev,
            [f.fieldKey]: "Please check or clarify this value.",
          }));
          setSubmitting(false);
          return;
        }
      }
      await onRowCompleted();
    } catch (err) {
      setGlobalError(
        err instanceof Error ? err.message : "Could not save table row.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleSkipRow = async () => {
    setSubmitting(true);
    setGlobalError(null);
    try {
      for (const f of tableRow.fields) {
        if (f.currentAnswerStatus !== "confirmed" && f.currentAnswerStatus !== "skipped") {
          await skipField(sessionId, f.fieldKey);
        }
      }
      await onRowCompleted();
    } catch (err) {
      setGlobalError(
        err instanceof Error ? err.message : "Could not skip table row.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="table-row-group-card">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3.5">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 shrink-0">
            <Table2 className="h-4 w-4" />
          </div>
          <div className="min-w-0 text-start">
            <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 leading-snug">
              {tableRow.tableTitle}
            </p>
            <div className="flex flex-wrap items-center gap-2 mt-0.5">
              <h2 className="text-base sm:text-lg font-bold text-white">
                Row {tableRow.rowIndex} of {tableRow.totalRows}
              </h2>
              {tableRow.rowLabel && (
                <span className="inline-flex items-center rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                  {tableRow.rowLabel}
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={onSwitchToSingleField}
          className="text-xs font-medium text-slate-400 hover:text-emerald-400 underline underline-offset-2 cursor-pointer shrink-0"
        >
          Fill one-by-one instead
        </button>
      </div>

      {tableRow.tableDescription && (
        <div className="rounded-xl border border-white/[0.08] bg-[#0A0E17] px-3.5 py-2.5 text-xs text-slate-300 leading-relaxed text-start">
          {tableRow.tableDescription}
        </div>
      )}

      {globalError && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-xs font-medium text-rose-200 text-start">
          {globalError}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {tableRow.fields.map((f) => (
          <div
            key={f.fieldKey}
            className="rounded-xl border border-white/[0.08] bg-[#0A0E17] p-3.5 space-y-2 text-start"
          >
            <label
              htmlFor={`field-${f.fieldKey}`}
              className="block text-xs font-semibold text-slate-200"
            >
              {f.label}
              {(f.required || f.requiredness === "required") && (
                <span className="ms-1 text-rose-400" aria-hidden="true">
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
              value={values[f.fieldKey] ?? ""}
              error={fieldErrors[f.fieldKey]}
              enableVoiceInput={false}
              onChange={(val) => {
                setFieldErrors((prev) => {
                  const next = { ...prev };
                  delete next[f.fieldKey];
                  return next;
                });
                setValues((prev) => ({ ...prev, [f.fieldKey]: val }));
              }}
            />
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-white/10">
        {allOptionalOrUnknown ? (
          <button
            type="button"
            disabled={submitting}
            onClick={handleSkipRow}
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 bg-[#0F1522] px-4 py-2.5 text-xs font-semibold text-slate-200 hover:border-emerald-500/40 hover:bg-[#151D2E] hover:text-white disabled:opacity-50 cursor-pointer"
          >
            <SkipForward className="h-3.5 w-3.5" />
            Skip Row
          </button>
        ) : (
          <div />
        )}

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
          Save Row &amp; Continue
        </button>
      </div>
    </div>
  );
}
