"use client";

import React from "react";
import { useTranslations } from "next-intl";
import {
  BooleanChild,
  unsatisfiedRequiredChildren,
} from "@/features/form-session/utils/questionRules";

interface DeclarationGroupProps {
  groupKey: string;
  label: string;
  children: BooleanChild[];
  onChange: (childKey: string, checked: boolean) => void;
  showErrors?: boolean;
  disabled?: boolean;
}

export function DeclarationGroup({
  groupKey,
  label,
  children,
  onChange,
  showErrors = false,
  disabled = false,
}: DeclarationGroupProps) {
  const t = useTranslations("common");
  const unsatisfied = new Set(
    unsatisfiedRequiredChildren(children).map((child) => child.key)
  );

  return (
    <fieldset
      data-testid={`declaration-group-${groupKey}`}
      className="space-y-2.5 border-0 p-0"
    >
      <legend className="text-sm font-semibold text-slate-100 mb-2">
        {label}
      </legend>

      {children.map((child) => {
        const inputId = `declaration-${child.key}`;
        const errorId = `${inputId}-error`;
        const showError = showErrors && unsatisfied.has(child.key);

        return (
          <div key={child.key} className="space-y-1.5">
            <label
              htmlFor={inputId}
              className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 transition-colors ${
                child.value === true
                  ? "border-emerald-500 bg-emerald-500/15 text-white ring-2 ring-emerald-500/20"
                  : "border-white/10 bg-[#0A0E17] hover:border-emerald-500/40 hover:bg-[#151D2E]"
              }`}
            >
              <input
                id={inputId}
                data-testid={`declaration-child-${child.key}`}
                type="checkbox"
                checked={child.value === true}
                disabled={disabled}
                aria-required={child.requiredness === "required"}
                aria-invalid={showError || undefined}
                aria-describedby={showError ? errorId : undefined}
                onChange={(event) => onChange(child.key, event.target.checked)}
                className="mt-0.5 h-4 w-4 shrink-0 rounded border-white/20 bg-[#0A0E17] accent-emerald-500"
              />
              <span className="text-sm text-slate-200 leading-snug">
                {child.label}
                {child.requiredness === "required" ? (
                  <span className="ms-1 text-rose-400" aria-hidden="true">
                    *
                  </span>
                ) : null}
                {child.requiredness !== "unknown" ? (
                  <span
                    data-testid={`declaration-requiredness-${child.key}`}
                    className="ms-2 rounded border border-white/10 bg-[#151D2E] px-1.5 py-0.5 text-[11px] font-medium text-slate-300"
                  >
                    {child.requiredness === "required"
                      ? t("required")
                      : t("optional")}
                  </span>
                ) : null}
              </span>
            </label>

            {showError ? (
              <p
                id={errorId}
                data-testid={`declaration-error-${child.key}`}
                role="alert"
                className="ps-3 text-xs font-medium text-rose-400"
              >
                {t("declarationRequired")}
              </p>
            ) : null}
          </div>
        );
      })}
    </fieldset>
  );
}
