"use client";

import React from "react";
import { useTranslations } from "next-intl";
import { AnswerResponse, CurrentField } from "../services/apiClient";
import { formatOriginalAnswer } from "../utils/formatProposedValue";

interface SessionClarificationPanelProps {
  currentField: CurrentField;
  lastAnswer: AnswerResponse;
  inputValue: string;
  clarifyValues: Record<string, string>;
  onClarifyValuesChange: (values: Record<string, string>) => void;
  onSubmit: (e: React.FormEvent) => void;
  onEdit: () => void;
}

export function SessionClarificationPanel({
  currentField,
  lastAnswer,
  inputValue,
  clarifyValues,
  onClarifyValuesChange,
  onSubmit,
  onEdit,
}: SessionClarificationPanelProps) {
  const t = useTranslations("workflow");
  const tc = useTranslations("common");

  if (!lastAnswer.clarification) return null;

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="space-y-1">
        <div className="inline-flex items-center gap-2 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-600" />
          Clarification Needed
        </div>
        <h2 className="text-xl sm:text-2xl font-bold text-slate-900 mt-2">
          {t("clarificationTitle")}
        </h2>
        <p className="text-sm text-slate-600">{t("clarificationSubtitle")}</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-1.5 text-start">
        <p className="text-[11px] uppercase tracking-wider font-semibold text-slate-500">
          {t("originalAnswerLabel")}
        </p>
        <p className="text-sm text-slate-900 font-medium">
          &ldquo;
          {formatOriginalAnswer(
            inputValue,
            currentField.fieldType,
            currentField.options,
          )}
          &rdquo;
        </p>
      </div>

      <div className="space-y-4">
        {lastAnswer.clarification.missing.map((key) => {
          const isSentenceReason = key.includes(" ") && key.length > 25;
          return (
            <div key={key} className="space-y-2 text-start">
              {isSentenceReason ? (
                <>
                  <p className="rounded-lg border border-amber-200 bg-amber-50/70 px-3.5 py-2.5 text-xs leading-relaxed text-amber-900">
                    {key}
                  </p>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                    {currentField.label || t("originalAnswerLabel")}
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
                      onClarifyValuesChange({
                        ...clarifyValues,
                        [key]: e.target.value,
                      })
                    }
                    required
                  >
                    <option value="" disabled className="bg-white text-slate-400">
                      Select currency...
                    </option>
                    <option value="EUR" className="bg-white text-slate-900">
                      EUR (€)
                    </option>
                    <option value="USD" className="bg-white text-slate-900">
                      USD ($)
                    </option>
                    <option value="GBP" className="bg-white text-slate-900">
                      GBP (£)
                    </option>
                  </select>
                  <div className="pointer-events-none absolute inset-y-0 end-0 flex items-center px-3.5 text-slate-500">
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                </div>
              ) : key === "period" ? (
                <div className="relative">
                  <select
                    className="input-field pe-10 appearance-none"
                    value={clarifyValues[key] || ""}
                    onChange={(e) =>
                      onClarifyValuesChange({
                        ...clarifyValues,
                        [key]: e.target.value,
                      })
                    }
                    required
                  >
                    <option value="" disabled className="bg-white text-slate-400">
                      Select frequency...
                    </option>
                    <option value="monthly" className="bg-white text-slate-900">
                      Monthly
                    </option>
                    <option value="yearly" className="bg-white text-slate-900">
                      Yearly
                    </option>
                    <option value="weekly" className="bg-white text-slate-900">
                      Weekly
                    </option>
                  </select>
                  <div className="pointer-events-none absolute inset-y-0 end-0 flex items-center px-3.5 text-slate-500">
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </div>
                </div>
              ) : (
                <input
                  type="text"
                  className="input-field"
                  value={clarifyValues[key] || ""}
                  onChange={(e) =>
                    onClarifyValuesChange({
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
          onClick={onEdit}
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
  );
}
