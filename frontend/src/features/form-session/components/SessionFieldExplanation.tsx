"use client";

import React from "react";
import { useTranslations } from "next-intl";
import { FieldExplanation } from "../services/apiClient";

interface SessionFieldExplanationProps {
  explanation: FieldExplanation;
  open: boolean;
  onToggle: () => void;
}

export function SessionFieldExplanation({
  explanation,
  open,
  onToggle,
}: SessionFieldExplanationProps) {
  const t = useTranslations("workflow");

  return (
    <div className="pt-1">
      <button
        type="button"
        data-testid="toggle-field-explanation"
        aria-expanded={open}
        onClick={onToggle}
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
        <span>{open ? t("hideExplainButton") : t("explainButton")}</span>
      </button>

      {open && (
        <div
          data-testid="field-explanation-panel"
          className="mt-3 rounded-xl border border-indigo-200/80 bg-indigo-50/50 p-4 space-y-3 text-start"
        >
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">
              {t("whatThisMeans")}
            </p>
            <p className="mt-0.5 text-xs leading-relaxed text-slate-800">
              {explanation.summary}
            </p>
          </div>
          <div className="border-t border-indigo-200/60 pt-2.5">
            <p className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">
              {t("whereToFindIt")}
            </p>
            <p className="mt-0.5 text-xs leading-relaxed text-slate-700">
              {explanation.whereToFind}
            </p>
          </div>
          {explanation.example && (
            <div className="border-t border-indigo-200/60 pt-2.5 flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">
                {t("exampleAnswer")}:
              </span>
              <code className="rounded bg-white border border-indigo-200 px-2 py-0.5 text-xs font-mono font-semibold text-slate-900">
                {explanation.example}
              </code>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
