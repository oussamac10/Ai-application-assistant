"use client";

import React, { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useLanguage } from "./LanguageProvider";
import { Mic, ChevronDown, AlertCircle } from "lucide-react";

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
  compactChoicePills?: boolean;
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
  compactChoicePills = false,
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
              className={`input-field focus-visible:ring-2 focus-visible:ring-emerald-500 focus:border-emerald-500 ${voiceCapableType ? "pe-11" : ""}`}
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
                    ? "bg-rose-500/15 text-rose-300 border border-rose-500/40 ring-4 ring-rose-500/20 animate-pulse motion-reduce:animate-none shadow-[0_0_12px_rgba(244,63,94,0.3)]"
                    : "text-slate-400 hover:bg-emerald-500/15 hover:text-emerald-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
                }`}
              >
                <Mic className={`h-4 w-4 ${isListening ? "animate-bounce motion-reduce:animate-none" : ""}`} />
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
              className="input-field resize-y focus-visible:ring-2 focus-visible:ring-emerald-500 focus:border-emerald-500"
              placeholder={placeholder}
              value={value}
              required={required}
              aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
              onChange={(e) => onChange(e.target.value)}
            />
            {limit && (
              <p className="text-end font-mono text-xs tabular-nums text-slate-400">
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
            className="input-field focus-visible:ring-2 focus-visible:ring-emerald-500 focus:border-emerald-500"
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
            className="input-field focus-visible:ring-2 focus-visible:ring-emerald-500 focus:border-emerald-500"
            placeholder={placeholder}
            value={value}
            required={required}
            aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
            onChange={(e) => onChange(e.target.value)}
          />
        );

      case "decimal":
      case "number":
        return (
          <input
            id={inputId}
            type="number"
            step="any"
            className="input-field focus-visible:ring-2 focus-visible:ring-emerald-500 focus:border-emerald-500"
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
            className="input-field focus-visible:ring-2 focus-visible:ring-emerald-500 focus:border-emerald-500"
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
            className="input-field focus-visible:ring-2 focus-visible:ring-emerald-500 focus:border-emerald-500"
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
              className={`flex items-center justify-center gap-2 rounded-xl border py-3 px-4 text-sm font-semibold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 ${
                isActive("true")
                  ? "border-emerald-500 bg-emerald-500/15 text-[var(--text-primary)] ring-2 ring-emerald-500/20 shadow-xs font-bold scale-[1.01]"
                  : "border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:border-emerald-500/40 hover:bg-[var(--bg-muted)] hover:text-[var(--text-primary)] active:scale-[0.99]"
              }`}
              onClick={() => handleBooleanChange("true")}
            >
              <span>{labels.yes}</span>
            </button>
            <button
              type="button"
              aria-pressed={isActive("false")}
              className={`flex items-center justify-center gap-2 rounded-xl border py-3 px-4 text-sm font-semibold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 ${
                isActive("false")
                  ? "border-emerald-500 bg-emerald-500/15 text-[var(--text-primary)] ring-2 ring-emerald-500/20 shadow-xs font-bold scale-[1.01]"
                  : "border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:border-emerald-500/40 hover:bg-[var(--bg-muted)] hover:text-[var(--text-primary)] active:scale-[0.99]"
              }`}
              onClick={() => handleBooleanChange("false")}
            >
              <span>{labels.no}</span>
            </button>
          </div>
        );
      }

      case "single_choice":
      case "choice":
        if (compactChoicePills && options.length >= 2 && options.length <= 6) {
          return (
            <div
              id={inputId}
              role="radiogroup"
              aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
              className="flex flex-wrap gap-2 w-full"
            >
              {options.map((opt) => {
                const isSelected = value === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    onClick={() => {
                      if (isSelected && !required) {
                        onChange("");
                      } else {
                        onChange(opt.value);
                      }
                    }}
                    className={`flex-1 min-w-[72px] inline-flex items-center justify-center rounded-xl border px-3 py-2 text-xs font-semibold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 ${
                      isSelected
                        ? "border-emerald-500 bg-emerald-500/15 text-[var(--text-primary)] ring-2 ring-emerald-500/20 shadow-xs font-bold"
                        : "border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:border-emerald-500/40 hover:bg-[var(--bg-muted)] hover:text-[var(--text-primary)]"
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          );
        }
        return (
          <div className="relative">
            <select
              id={inputId}
              className="input-field pe-10 appearance-none cursor-pointer focus-visible:ring-2 focus-visible:ring-emerald-500 focus:border-emerald-500"
              value={value}
              required={required}
              aria-describedby={`${helpText ? descId : ""} ${error ? errorId : ""}`}
              onChange={(e) => onChange(e.target.value)}
            >
              <option value="" disabled>
                Select an option...
              </option>
              {options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 end-0 flex items-center px-3.5 text-[var(--text-muted)]">
              <ChevronDown className="h-4 w-4" />
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
                  className={`flex items-center gap-3.5 rounded-xl border px-4 py-3 cursor-pointer select-none transition-all duration-150 focus-within:ring-2 focus-within:ring-emerald-500 ${
                    isChecked
                      ? "border-emerald-500 bg-emerald-500/15 text-[var(--text-primary)] ring-2 ring-emerald-500/20 shadow-xs font-semibold"
                      : "border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:border-emerald-500/40 hover:bg-[var(--bg-muted)] hover:text-[var(--text-primary)] active:scale-[0.99]"
                  }`}
                >
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-emerald-500 focus:ring-emerald-500/30 cursor-pointer accent-emerald-500 focus-visible:ring-2 focus-visible:ring-emerald-500"
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
            className="input-field focus-visible:ring-2 focus-visible:ring-emerald-500 focus:border-emerald-500"
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
            className="input-field resize-y focus-visible:ring-2 focus-visible:ring-emerald-500 focus:border-emerald-500"
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
            className="input-field focus-visible:ring-2 focus-visible:ring-emerald-500 focus:border-emerald-500"
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
        <p id={descId} className="text-sm text-slate-400 leading-relaxed">
          {helpText}
        </p>
      )}
      <div className="mt-1">{renderInput()}</div>
      {error && (
        <div
          id={errorId}
          className="mt-2 flex items-center gap-2 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-600 dark:text-rose-200"
          role="alert"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-500 dark:text-rose-400" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
