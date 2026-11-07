"use client";

import React, { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useLanguage } from "./LanguageProvider";

const BOOLEAN_LABELS: Record<string, { yes: string; no: string }> = {
  ar: { yes: "نعم", no: "لا" },
  de: { yes: "Ja", no: "Nein" },
  en: { yes: "Yes", no: "No" },
  fr: { yes: "Oui", no: "Non" },
  es: { yes: "Sí", no: "No" },
  tr: { yes: "Evet", no: "Hayır" },
  uk: { yes: "Так", no: "Ні" },
  ru: { yes: "Да", no: "Нет" },
  it: { yes: "Sì", no: "No" },
  pl: { yes: "Tak", no: "Nie" },
  pt: { yes: "Sim", no: "Não" },
};

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
  enableVoiceInput?: boolean;
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
  enableVoiceInput = false,
}: FieldRendererProps) {
  const t = useTranslations("common");
  let activeLocale = "en";
  try {
    const lang = useLanguage();
    if (lang?.locale) activeLocale = lang.locale;
  } catch {
    // fallback if outside LanguageProvider
  }
  const inputId = `field-${fieldKey}`;
  const errorId = `error-${fieldKey}`;
  const descId = `desc-${fieldKey}`;
  const [isListening, setIsListening] = useState(false);

  const handleVoiceDictation = useCallback(() => {
    if (typeof window === "undefined") return;
    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) return;

    try {
      const recognition = new SpeechRecognitionCtor();
      recognition.lang = document.documentElement.lang || "en";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      setIsListening(true);
      recognition.onresult = (event: any) => {
        const transcript = event?.results?.[0]?.[0]?.transcript;
        if (transcript) {
          onChange(value ? `${value} ${transcript}` : transcript);
        }
        setIsListening(false);
      };
      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);
      recognition.start();
    } catch {
      setIsListening(false);
    }
  }, [onChange, value]);

  const voiceCapableType =
    enableVoiceInput &&
    (fieldType === "string" ||
      fieldType === "person_name" ||
      fieldType === "country" ||
      fieldType === "address" ||
      fieldType === "multiline_text" ||
      fieldType === "money");

  const renderInput = () => {
    switch (fieldType) {
      case "string":
      case "person_name":
      case "country":
        return (
          <div className="relative w-full">
            <input
              id={inputId}
              type="text"
              className={`input-field ${voiceCapableType ? "pe-11" : ""}`}
              placeholder={placeholder}
              value={value}
              required={required}
              aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
              onChange={(e) => onChange(e.target.value)}
            />
            {voiceCapableType && (
              <button
                type="button"
                onClick={handleVoiceDictation}
                aria-label="Voice dictation"
                title={isListening ? "Listening..." : "Speak your answer"}
                data-testid="voice-dictation-btn"
                className={`absolute inset-y-1.5 end-1.5 flex items-center justify-center rounded-lg px-2.5 transition ${
                  isListening
                    ? "bg-rose-100 text-rose-700 border border-rose-300"
                    : "text-slate-400 hover:bg-slate-100 hover:text-indigo-600"
                }`}
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                  />
                </svg>
              </button>
            )}
          </div>
        );

      case "multiline_text": {
        const limit = configuration?.maxLength;
        return (
          <div className="space-y-1.5 w-full">
            <textarea
              id={inputId}
              rows={4}
              className="input-field resize-y"
              placeholder={placeholder}
              value={value}
              required={required}
              aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
              onChange={(e) => onChange(e.target.value)}
            />
            {limit && (
              <p className="text-end font-mono text-xs tabular-nums text-slate-500">
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
            className="input-field"
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
            className="input-field"
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
            className="input-field"
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
            className="input-field"
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
            className="input-field"
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
        const labels = BOOLEAN_LABELS[activeLocale] || BOOLEAN_LABELS.en;

        return (
          <div
            className="grid grid-cols-2 gap-3 w-full"
            id={inputId}
            role="group"
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
          >
            <button
              type="button"
              aria-pressed={isActive("true")}
              className={`flex items-center justify-center gap-2 rounded-xl border py-3.5 px-4 text-sm font-semibold transition-colors ${
                isActive("true")
                  ? "border-indigo-500 bg-indigo-50 text-indigo-900 ring-1 ring-indigo-500/40"
                  : "border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50 hover:text-slate-900"
              }`}
              onClick={() => handleBooleanChange("true")}
            >
              <span>{labels.yes}</span>
            </button>
            <button
              type="button"
              aria-pressed={isActive("false")}
              className={`flex items-center justify-center gap-2 rounded-xl border py-3.5 px-4 text-sm font-semibold transition-colors ${
                isActive("false")
                  ? "border-indigo-500 bg-indigo-50 text-indigo-900 ring-1 ring-indigo-500/40"
                  : "border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50 hover:text-slate-900"
              }`}
              onClick={() => handleBooleanChange("false")}
            >
              <span>{labels.no}</span>
            </button>
          </div>
        );
      }

      case "single_choice":
        return (
          <div className="relative">
            <select
              id={inputId}
              className="input-field pe-10 appearance-none cursor-pointer"
              value={value}
              required={required}
              aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
              onChange={(e) => onChange(e.target.value)}
            >
              <option value="" disabled className="text-slate-400 bg-white">
                Select an option...
              </option>
              {options.map((opt) => (
                <option
                  key={opt.value}
                  value={opt.value}
                  className="bg-white text-slate-900"
                >
                  {opt.label}
                </option>
              ))}
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
            className="w-full space-y-2"
          >
            {options.map((opt) => {
              const isChecked = currentValues.includes(opt.value);
              return (
                <label
                  key={opt.value}
                  className={`flex items-center gap-3 rounded-xl border px-4 py-3 cursor-pointer select-none transition-colors ${
                    isChecked
                      ? "border-indigo-500 bg-indigo-50/80 text-indigo-950"
                      : "border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50"
                  }`}
                >
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 bg-white text-indigo-600 focus:ring-indigo-500/30 cursor-pointer accent-indigo-600"
                    checked={isChecked}
                    onChange={(e) =>
                      handleCheckboxChange(opt.value, e.target.checked)
                    }
                  />
                  <span className="text-sm font-medium">{opt.label}</span>
                </label>
              );
            })}
          </div>
        );
      }

      case "money": {
        return (
          <input
            id={inputId}
            type="text"
            className="input-field"
            placeholder={placeholder || "e.g. 2000 EUR"}
            value={value}
            required={required}
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          />
        );
      }

      case "address":
        return (
          <textarea
            id={inputId}
            rows={3}
            className="input-field resize-y"
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
            className="input-field"
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
    <div className="w-full space-y-2 text-start">
      {helpText && (
        <p id={descId} className="text-sm text-slate-600 leading-relaxed">
          {helpText}
        </p>
      )}
      <div className="mt-1">{renderInput()}</div>
      {error && (
        <div
          id={errorId}
          className="mt-2 flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-800"
          role="alert"
        >
          <svg
            className="h-4 w-4 shrink-0 text-rose-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
