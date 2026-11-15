"use client";

import React from "react";
import { useTranslations } from "next-intl";
import { FieldExplanation } from "../services/apiClient";
import { HelpCircle } from "lucide-react";

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
        className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-400 transition-colors hover:bg-emerald-500/20 hover:text-emerald-300"
      >
        <HelpCircle className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
        <span>{open ? t("hideExplainButton") : t("explainButton")}</span>
      </button>

      {open && (
        <div
          data-testid="field-explanation-panel"
          className="mt-3 rounded-xl border border-emerald-500/25 bg-[#0A0E17] p-4 space-y-3 text-start"
        >
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
              {t("whatThisMeans")}
            </p>
            <p className="mt-0.5 text-xs leading-relaxed text-slate-200">
              {explanation.summary}
            </p>
          </div>
          <div className="border-t border-white/[0.08] pt-2.5">
            <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
              {t("whereToFindIt")}
            </p>
            <p className="mt-0.5 text-xs leading-relaxed text-slate-300">
              {explanation.whereToFind}
            </p>
          </div>
          {explanation.example && (
            <div className="border-t border-white/[0.08] pt-2.5 flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
                {t("exampleAnswer")}:
              </span>
              <code className="rounded bg-[#151D2E] border border-emerald-500/30 px-2 py-0.5 text-xs font-mono font-semibold text-emerald-300">
                {explanation.example}
              </code>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
