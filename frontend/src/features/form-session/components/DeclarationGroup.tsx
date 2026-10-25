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
      <legend className="text-sm font-semibold text-slate-800 mb-2">
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
                  ? "border-indigo-500 bg-indigo-50/70"
                  : "border-slate-300 bg-white hover:border-slate-400 hover:bg-slate-50"
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
                className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 bg-white accent-indigo-600"
              />
              <span className="text-sm text-slate-800 leading-snug">
                {child.label}
                {child.requiredness === "required" ? (
                  <span className="ms-1 text-rose-600" aria-hidden="true">
                    *
                  </span>
                ) : null}
                {child.requiredness !== "unknown" ? (
                  <span
                    data-testid={`declaration-requiredness-${child.key}`}
                    className="ms-2 rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600"
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
                className="ps-3 text-xs font-medium text-rose-600"
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
