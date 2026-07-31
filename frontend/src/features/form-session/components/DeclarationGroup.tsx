"use client";

import React from "react";
import { useTranslations } from "next-intl";
import {
  BooleanChild,
  unsatisfiedRequiredChildren,
} from "@/features/form-session/utils/questionRules";

/**
 * A block of independent consents, rendered as independent controls.
 *
 * The backend models these as separate booleans, each carrying the requiredness
 * its own marker declared:
 *
 *     Je certifie que les informations sont exactes *   -> required
 *     J'accepte le traitement des donnees de test *     -> required
 *     Je souhaite recevoir des nouvelles (Optional)     -> optional
 *
 * Rendered as one multiple-choice question they became "tick any of these", and
 * the two mandatory consents silently stopped being mandatory. They are not
 * options of a question; they are three yes/no answers that happen to sit
 * together, and each needs its own control, its own requiredness and its own
 * error.
 *
 * A `fieldset`/`legend` rather than a styled div: it is what tells a screen
 * reader these checkboxes belong together, which is the whole semantic content
 * of the grouping.
 */

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
    unsatisfiedRequiredChildren(children).map((child) => child.key),
  );

  return (
    <fieldset
      data-testid={`declaration-group-${groupKey}`}
      className="space-y-3 border-0 p-0"
    >
      <legend className="text-sm font-semibold text-slate-300">{label}</legend>

      {children.map((child) => {
        const inputId = `declaration-${child.key}`;
        const errorId = `${inputId}-error`;
        const showError = showErrors && unsatisfied.has(child.key);

        return (
          <div key={child.key} className="space-y-1">
            <label
              htmlFor={inputId}
              className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-800 bg-slate-950/40 p-3 transition hover:border-slate-700"
            >
              <input
                id={inputId}
                data-testid={`declaration-child-${child.key}`}
                type="checkbox"
                checked={child.value === true}
                disabled={disabled}
                // Each child carries its own required state, so assistive
                // technology announces exactly the two that must be checked
                // rather than the block as a whole.
                aria-required={child.requiredness === "required"}
                aria-invalid={showError || undefined}
                aria-describedby={showError ? errorId : undefined}
                onChange={(event) => onChange(child.key, event.target.checked)}
                className="mt-0.5 h-5 w-5 shrink-0 accent-indigo-500"
              />
              <span className="text-sm text-slate-200">
                {child.label}
                {child.requiredness === "required" ? (
                  <span className="ms-1 text-rose-400" aria-hidden="true">
                    *
                  </span>
                ) : null}
                {/* Only a real finding is labelled. `unknown` says nothing,
                    because the document said nothing. */}
                {child.requiredness !== "unknown" ? (
                  <span
                    data-testid={`declaration-requiredness-${child.key}`}
                    className="ms-2 text-xs font-medium tracking-wide text-slate-400"
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
                className="ps-3 text-sm text-rose-400"
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
