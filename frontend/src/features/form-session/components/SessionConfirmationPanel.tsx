"use client";

import React from "react";
import { useTranslations } from "next-intl";
import { AnswerResponse, CurrentField } from "../services/apiClient";
import {
  formatOriginalAnswer,
  formatProposedValue,
} from "../utils/formatProposedValue";

interface SessionConfirmationPanelProps {
  currentField: CurrentField;
  lastAnswer: AnswerResponse;
  inputValue: string;
  onEdit: () => void;
  onConfirm: () => void;
}

export function SessionConfirmationPanel({
  currentField,
  lastAnswer,
  inputValue,
  onEdit,
  onConfirm,
}: SessionConfirmationPanelProps) {
  const t = useTranslations("workflow");
  const tc = useTranslations("common");

  const normalizedObj =
    lastAnswer.normalizedValue && typeof lastAnswer.normalizedValue === "object"
      ? (lastAnswer.normalizedValue as {
          width?: number;
          height?: number;
          strokes?: Array<Array<[number, number]>>;
        })
      : null;

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-600" />
          Value Standardized
        </div>
        <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight mt-2">
          {t("confirmTitle")}
        </h2>
        <p className="text-xs text-slate-600">
          Please confirm that the standardized value matches your intention
        </p>
      </div>

      <div className="space-y-3">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-1.5 text-start">
          <p className="text-[11px] uppercase tracking-wider font-semibold text-slate-500">
            {t("originalAnswerLabel")}
          </p>
          <p className="text-sm text-slate-800 font-medium">
            &ldquo;
            {currentField.fieldType === "signature"
              ? formatOriginalAnswer(
                  inputValue,
                  currentField.fieldType,
                  currentField.options,
                ) || "Hand-drawn signature"
              : formatOriginalAnswer(
                  inputValue,
                  currentField.fieldType,
                  currentField.options,
                )}
            &rdquo;
          </p>
        </div>

        <div className="rounded-xl border border-indigo-200 bg-indigo-50/70 p-5 space-y-2 text-start">
          <div className="flex items-center justify-between">
            <p className="text-[11px] uppercase font-bold text-indigo-700 tracking-wider">
              {t("proposedValueLabel")}
            </p>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
              <svg
                className="h-3 w-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              Ready for Form
            </span>
          </div>
          {currentField.fieldType === "signature" &&
          normalizedObj &&
          Array.isArray(normalizedObj.strokes) ? (
            <div className="space-y-2 pt-1">
              <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                <svg
                  viewBox={`0 0 ${normalizedObj.width || 600} ${normalizedObj.height || 200}`}
                  className="h-24 w-full"
                  aria-label="Signature preview"
                >
                  {normalizedObj.strokes.map((stroke, idx) =>
                    stroke.length > 0 ? (
                      <polyline
                        key={idx}
                        fill="none"
                        stroke="#0f172a"
                        strokeWidth={2.75}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points={stroke.map(([x, y]) => `${x},${y}`).join(" ")}
                      />
                    ) : null,
                  )}
                </svg>
              </div>
              <p className="text-xs font-medium text-slate-600">
                {formatProposedValue(
                  lastAnswer.normalizedValue,
                  lastAnswer.outputValue,
                  currentField.fieldType,
                )}
              </p>
            </div>
          ) : (
            <p className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
              {formatProposedValue(
                lastAnswer.normalizedValue,
                lastAnswer.outputValue,
                currentField.fieldType,
              )}
            </p>
          )}
        </div>
      </div>

      <div className="flex gap-3 pt-2">
        <button
          type="button"
          onClick={onEdit}
          className="btn-secondary flex-1 py-3.5 text-sm font-medium"
        >
          <span>{tc("edit")}</span>
          <kbd className="hidden sm:inline-block rounded bg-slate-100 border border-slate-300 px-1.5 py-0.5 text-[10px] font-mono text-slate-600">
            Esc
          </kbd>
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className="btn-primary flex-1 py-3.5 text-sm font-semibold"
        >
          <span>{tc("confirm")}</span>
          <kbd className="hidden sm:inline-block rounded bg-indigo-700 border border-indigo-500 px-1.5 py-0.5 text-[10px] font-mono text-indigo-100">
            ↵ Enter
          </kbd>
        </button>
      </div>
    </div>
  );
}
