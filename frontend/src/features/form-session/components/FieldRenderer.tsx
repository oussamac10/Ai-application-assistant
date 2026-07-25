"use client";

import React from "react";
import { useTranslations } from "next-intl";

interface FieldRendererProps {
  fieldType: string;
  fieldKey: string;
  required: boolean;
  configuration: Record<string, any>;
  options: Array<{ value: string; label: string }>;
  value: string;
  onChange: (val: string) => void;
  error?: string;
  placeholder?: string;
  helpText?: string;
}

export function FieldRenderer({
  fieldType,
  fieldKey,
  required,
  configuration,
  options,
  value,
  onChange,
  error,
  placeholder = "",
  helpText,
}: FieldRendererProps) {
  const t = useTranslations("common");
  const inputId = `field-${fieldKey}`;
  const errorId = `error-${fieldKey}`;
  const descId = `desc-${fieldKey}`;

  const renderInput = () => {
    switch (fieldType) {
      case "string":
      case "person_name":
      case "country":
        return (
          <input
            id={inputId}
            type="text"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 placeholder-slate-500 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
            placeholder={placeholder}
            value={value}
            required={required}
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          />
        );

      case "multiline_text": {
        const limit = configuration?.maxLength;
        return (
          <div className="space-y-1 w-full">
            <textarea
              id={inputId}
              rows={4}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 placeholder-slate-500 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 resize-y"
              placeholder={placeholder}
              value={value}
              required={required}
              aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
              onChange={(e) => onChange(e.target.value)}
            />
            {limit && (
              <p className="text-right text-xs text-slate-500">
                {value.length} / {limit}
              </p>
            )}
          </div>
        );
      }

      case "date":
        return (
          <input
            id={inputId}
            type="date"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
            value={value}
            required={required}
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          />
        );

      case "integer":
        return (
          <input
            id={inputId}
            type="number"
            step="1"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 placeholder-slate-500 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
            placeholder={placeholder}
            value={value}
            required={required}
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          />
        );

      case "decimal":
        return (
          <input
            id={inputId}
            type="number"
            step="any"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 placeholder-slate-500 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
            placeholder={placeholder}
            value={value}
            required={required}
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          />
        );

      case "email":
        return (
          <input
            id={inputId}
            type="email"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 placeholder-slate-500 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
            placeholder={placeholder}
            value={value}
            required={required}
            dir="ltr"
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          />
        );

      case "phone":
        return (
          <input
            id={inputId}
            type="tel"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 placeholder-slate-500 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
            placeholder={placeholder}
            value={value}
            required={required}
            dir="ltr"
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          />
        );

      case "boolean": {
        const handleBooleanChange = (boolVal: string) => {
          onChange(boolVal);
        };
        const isActive = (val: string) => value === val;

        return (
          <div className="flex gap-4 w-full" id={inputId} role="group" aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}>
            <button
              type="button"
              className={`flex-1 rounded-xl border py-3.5 text-base font-semibold transition ${
                isActive("true")
                  ? "border-indigo-500 bg-indigo-500/10 text-indigo-400"
                  : "border-slate-700 bg-slate-950 text-slate-300 hover:bg-slate-900"
              }`}
              onClick={() => handleBooleanChange("true")}
            >
              Yes
            </button>
            <button
              type="button"
              className={`flex-1 rounded-xl border py-3.5 text-base font-semibold transition ${
                isActive("false")
                  ? "border-indigo-500 bg-indigo-500/10 text-indigo-400"
                  : "border-slate-700 bg-slate-950 text-slate-300 hover:bg-slate-900"
              }`}
              onClick={() => handleBooleanChange("false")}
            >
              No
            </button>
          </div>
        );
      }

      case "single_choice":
        return (
          <select
            id={inputId}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 appearance-none"
            value={value}
            required={required}
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          >
            <option value="" disabled className="text-slate-500">
              Select an option...
            </option>
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );

      case "multiple_choice": {
        let currentValues: string[] = [];
        try {
          currentValues = JSON.parse(value);
          if (!Array.isArray(currentValues)) currentValues = [];
        } catch {
          if (value) currentValues = [value];
        }

        const handleCheckboxChange = (optVal: string, checked: boolean) => {
          let nextValues = [...currentValues];
          if (checked) {
            if (!nextValues.includes(optVal)) nextValues.push(optVal);
          } else {
            nextValues = nextValues.filter((v) => v !== optVal);
          }
          onChange(JSON.stringify(nextValues));
        };

        return (
          <div
            id={inputId}
            role="group"
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            className="w-full space-y-3 rounded-xl border border-slate-800 bg-slate-950/40 p-4"
          >
            {options.map((opt) => {
              const isChecked = currentValues.includes(opt.value);
              return (
                <label key={opt.value} className="flex items-center gap-3 cursor-pointer select-none text-slate-300">
                  <input
                    type="checkbox"
                    className="h-5 w-5 rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500/20"
                    checked={isChecked}
                    onChange={(e) => handleCheckboxChange(opt.value, e.target.checked)}
                  />
                  <span className="text-base">{opt.label}</span>
                </label>
              );
            })}
          </div>
        );
      }

      case "money": {
        // Expected backend format or free text.
        // If money value is compound, it can be structured as amount, currency, period.
        // We will return free text string if money is handled as free text answer first.
        // If money is entered as a text, e.g. "2000 EUR per month", preserve it.
        return (
          <input
            id={inputId}
            type="text"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 placeholder-slate-500 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
            placeholder={placeholder || "e.g. 2,000 EUR monthly"}
            value={value}
            required={required}
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          />
        );
      }

      case "address":
        // Address compound layout entered as text description or struct.
        // We preserve entered value as text.
        return (
          <textarea
            id={inputId}
            rows={3}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 placeholder-slate-500 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 resize-y"
            placeholder={placeholder || "Street, Postal Code, City, Country"}
            value={value}
            required={required}
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          />
        );

      default:
        return (
          <input
            id={inputId}
            type="text"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3.5 text-base text-slate-100 placeholder-slate-500 shadow-inner outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
            placeholder={placeholder}
            value={value}
            required={required}
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          />
        );
    }
  };

  return (
    <div className="w-full space-y-2 text-left">
      {helpText && (
        <p id={descId} className="text-sm text-slate-400">
          {helpText}
        </p>
      )}
      <div className="mt-1">{renderInput()}</div>
      {error && (
        <p id={errorId} className="text-sm text-rose-400 font-medium animate-pulse" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
