"use client";

import React from "react";
import {
  ChevronDown,
  ChevronUp,
  Globe,
  Loader2,
  Sparkles,
  Trash2,
} from "lucide-react";
import { ModernSelect } from "@/components/ui/ModernSelect";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import type { AutoMapFieldResult, FormFieldItem } from "../../types";
import { CANONICAL_VAULT_KEYS, FIELD_TYPE_OPTIONS } from "./constants";

export interface ReviewStudioFieldCardProps {
  field: FormFieldItem;
  index: number;
  totalFields: number;
  canEdit: boolean;
  isHighlighted: boolean;
  sourceLanguage: string;
  supportedLanguages: string[];
  autoMapSuggestion?: AutoMapFieldResult;
  expandedTranslationsFieldId: string | null;
  setExpandedTranslationsFieldId: (id: string | null) => void;
  activeTranslationLang: string;
  setActiveTranslationLang: (lang: string) => void;
  translatingFieldId: string | null;
  onSelectField: (fieldId: string, page?: number) => void;
  onFieldChange: (
    fieldId: string,
    updates: Partial<FormFieldItem> & { label?: string; helpText?: string }
  ) => void;
  onFieldTranslationChange: (
    fieldId: string,
    language: string,
    newLabel: string
  ) => void;
  onAutoTranslateField: (fieldId: string, specificLang?: string) => void;
  onMoveField: (index: number, direction: "up" | "down") => void;
  onDeleteField: (fieldId: string) => void;
}

export function ReviewStudioFieldCard({
  field,
  index,
  totalFields,
  canEdit,
  isHighlighted,
  sourceLanguage,
  supportedLanguages,
  autoMapSuggestion,
  expandedTranslationsFieldId,
  setExpandedTranslationsFieldId,
  activeTranslationLang,
  setActiveTranslationLang,
  translatingFieldId,
  onSelectField,
  onFieldChange,
  onFieldTranslationChange,
  onAutoTranslateField,
  onMoveField,
  onDeleteField,
}: ReviewStudioFieldCardProps) {
  const primaryLabel = field.translations?.[0]?.label || field.key;
  const isRequired = field.requiredness === "required" || field.required;
  const fPage =
    typeof field.configuration?.page === "number"
      ? field.configuration.page
      : 1;
  const hasBbox = Array.isArray(field.configuration?.bbox);

  return (
    <div
      id={`field-card-${field.id}`}
      onClick={() => onSelectField(field.id, hasBbox ? fPage : undefined)}
      className={`p-4 rounded-xl border transition-all shadow-card group cursor-pointer ${
        isHighlighted
          ? "border-emerald-500/80 bg-emerald-500/[0.04] ring-2 ring-emerald-500/40 shadow-[0_0_12px_rgba(16,185,129,0.15)]"
          : "border-slate-800 hover:border-slate-700 bg-[#0F1522]"
      }`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span
            className={`w-6 h-6 rounded-lg text-xs font-mono font-bold flex items-center justify-center shrink-0 ${
              isHighlighted
                ? "bg-emerald-500 text-slate-950 shadow-2xs"
                : "bg-slate-800 text-slate-400 border border-slate-700"
            }`}
          >
            {index + 1}
          </span>
          <input
            type="text"
            disabled={!canEdit}
            value={primaryLabel}
            onChange={(e) =>
              onFieldChange(field.id, { label: e.target.value })
            }
            className="text-sm font-bold text-white bg-transparent border-b border-transparent hover:border-slate-700 focus:border-emerald-500 focus:outline-none px-1 py-0.5 w-full"
          />
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {canEdit && (
            <>
              <button
                type="button"
                disabled={index === 0}
                onClick={(e) => {
                  e.stopPropagation();
                  onMoveField(index, "up");
                }}
                className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-20 ml-1 cursor-pointer transition-colors"
                title="Move Up"
              >
                <ChevronUp className="w-4 h-4" />
              </button>
              <button
                type="button"
                disabled={index === totalFields - 1}
                onClick={(e) => {
                  e.stopPropagation();
                  onMoveField(index, "down");
                }}
                className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-20 cursor-pointer transition-colors"
                title="Move Down"
              >
                <ChevronDown className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteField(field.id);
                }}
                className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-red-500/10 ml-1 cursor-pointer transition-colors"
                title="Delete Field"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Field Parameters Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2.5 border-t border-slate-800">
        {/* Type */}
        <div>
          <label className="block text-[11px] font-mono font-semibold text-slate-400 mb-1 uppercase tracking-wider">
            Input Type
          </label>
          <ModernSelect
            disabled={!canEdit}
            value={field.fieldType}
            onChange={(val) => onFieldChange(field.id, { fieldType: val })}
            options={FIELD_TYPE_OPTIONS}
            size="sm"
            aria-label="Input Type"
          />
        </div>

        {/* Requirement */}
        <div>
          <label className="block text-[11px] font-mono font-semibold text-slate-400 mb-1 uppercase tracking-wider">
            Requirement
          </label>
          <ModernSelect
            disabled={!canEdit}
            value={isRequired ? "required" : "optional"}
            onChange={(val) =>
              onFieldChange(field.id, {
                requiredness: val,
                required: val === "required",
              })
            }
            options={[
              { value: "required", label: "Required for Citizen" },
              { value: "optional", label: "Optional" },
            ]}
            size="sm"
            aria-label="Requirement"
          />
        </div>

        {/* Saved Details Auto-Fill Link */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-400 mb-1">
            Auto-Fill from Saved Details
          </label>
          <ModernSelect
            disabled={!canEdit}
            value={field.questionKey || ""}
            onChange={(val) =>
              onFieldChange(field.id, {
                questionKey: val || null,
              })
            }
            options={[
              { value: "", label: "No auto-fill (custom question)" },
              ...CANONICAL_VAULT_KEYS.map((k) => ({
                value: k.key,
                label: k.label,
              })),
            ]}
            searchable
            searchPlaceholder="Search saved details..."
            size="sm"
            aria-label="Auto-Fill from Saved Details"
          />
          {autoMapSuggestion && autoMapSuggestion.suggested_question_key && (() => {
            const suggestedHumanLabel =
              CANONICAL_VAULT_KEYS.find((k) => k.key === autoMapSuggestion.suggested_question_key)?.label ||
              (autoMapSuggestion.suggested_question_key === "person.date_of_birth"
                ? "Date of Birth"
                : autoMapSuggestion.suggested_question_key
                    .split(".")
                    .pop()
                    ?.replace(/_/g, " ")
                    .replace(/\b\w/g, (c) => c.toUpperCase()) ||
                  autoMapSuggestion.suggested_question_key);

            return (
              <div className="mt-1.5 flex items-center justify-between text-[11px] bg-emerald-500/10 border border-emerald-500/30 px-2 py-1 rounded-lg">
                <span className="text-emerald-300 flex items-center gap-1 font-medium truncate mr-1">
                  <Sparkles className="w-3 h-3 text-emerald-400 shrink-0" />
                  <span className="truncate">
                    Suggested: <span className="text-emerald-300 font-bold">{suggestedHumanLabel}</span> ({Math.round(autoMapSuggestion.confidence * 100)}%)
                  </span>
                </span>
                {canEdit && field.questionKey !== autoMapSuggestion.suggested_question_key && (
                  <button
                    type="button"
                    onClick={() =>
                      onFieldChange(field.id, {
                        questionKey: autoMapSuggestion.suggested_question_key,
                      })
                    }
                    className="shrink-0 text-[10px] font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 px-2 py-0.5 rounded cursor-pointer transition-colors shadow-2xs"
                    title={autoMapSuggestion.match_reason}
                  >
                    Apply
                  </button>
                )}
              </div>
            );
          })()}
        </div>
      </div>

      {/* Citizen Guidance Translations Toggle Bar */}
      <div className="mt-3 pt-2.5 border-t border-slate-800 flex items-center justify-between">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setExpandedTranslationsFieldId(
              expandedTranslationsFieldId === field.id ? null : field.id
            );
          }}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-emerald-400 cursor-pointer transition-colors"
        >
          <Globe className="w-3.5 h-3.5 text-emerald-400" />
          <span>Question Translations</span>
          <span className="text-[10px] bg-slate-800 text-emerald-400 font-bold px-1.5 py-0.5 rounded-full border border-slate-700">
            {field.translations?.length || 1}
          </span>
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform ${
              expandedTranslationsFieldId === field.id ? "rotate-180" : ""
            }`}
          />
        </button>

        {canEdit && (
          <button
            type="button"
            disabled={translatingFieldId === field.id}
            onClick={(e) => {
              e.stopPropagation();
              onAutoTranslateField(field.id);
            }}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-lg transition disabled:opacity-50 cursor-pointer"
            title="Translate this question into all supported languages"
          >
            {translatingFieldId === field.id ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            )}
            <span>Translate All</span>
          </button>
        )}
      </div>

      {/* Expandable Multilingual Translations Drawer */}
      {expandedTranslationsFieldId === field.id && (
        <div
          className="mt-3 p-3 bg-[#0A0E17]/80 rounded-xl border border-slate-800 space-y-3"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-400">
              Applicant Language
            </span>
            <span className="text-[10px] text-slate-500 font-mono">
              Original Form: {sourceLanguage.toUpperCase() || "EN"}
            </span>
          </div>

          {/* Language Tabs */}
          <div className="flex flex-wrap gap-1.5">
            {supportedLanguages.map((code) => {
              const langObj = UNIVERSAL_LANGUAGES.find((l) => l.code === code);
              const label = langObj
                ? `${langObj.nativeName} (${code.toUpperCase()})`
                : code.toUpperCase();
              const isSelected = activeTranslationLang === code;
              const transForCode = field.translations?.find(
                (t) => t.language === code
              );
              const hasTranslation = Boolean(transForCode?.label?.trim());

              return (
                <button
                  key={code}
                  type="button"
                  onClick={() => setActiveTranslationLang(code)}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono font-semibold transition border cursor-pointer ${
                    isSelected
                      ? "bg-emerald-500 text-slate-950 border-emerald-500 shadow-2xs font-bold"
                      : "bg-[#0F1522] text-slate-300 border-slate-800 hover:bg-slate-800"
                  }`}
                >
                  <span>{label}</span>
                  {hasTranslation && (
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isSelected ? "bg-slate-950" : "bg-emerald-400"
                      }`}
                    />
                  )}
                </button>
              );
            })}
          </div>

          {/* Active Language Editor */}
          {(() => {
            const activeLangObj = UNIVERSAL_LANGUAGES.find(
              (l) => l.code === activeTranslationLang
            );
            const isRtl = activeLangObj?.dir === "rtl";
            const currentTrans = field.translations?.find(
              (t) => t.language === activeTranslationLang
            );
            const currentTransVal = currentTrans?.label || "";
            const isSourceLang =
              activeTranslationLang === (sourceLanguage || "de");

            return (
              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-300">
                    Question Label in{" "}
                    {activeLangObj?.englishName ||
                      activeTranslationLang.toUpperCase()}{" "}
                    {isRtl ? "(RTL)" : ""}
                  </label>
                  {canEdit && !isSourceLang && (
                    <button
                      type="button"
                      disabled={translatingFieldId === field.id}
                      onClick={() =>
                        onAutoTranslateField(field.id, activeTranslationLang)
                      }
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 hover:text-emerald-300 disabled:opacity-50 cursor-pointer"
                    >
                      {translatingFieldId === field.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                      )}
                      <span>Auto-Translate This</span>
                    </button>
                  )}
                </div>
                <input
                  type="text"
                  disabled={!canEdit}
                  dir={isRtl ? "rtl" : "ltr"}
                  value={currentTransVal}
                  onChange={(e) =>
                    onFieldTranslationChange(
                      field.id,
                      activeTranslationLang,
                      e.target.value
                    )
                  }
                  placeholder={
                    isSourceLang
                      ? primaryLabel
                      : `Enter translated label in ${
                          activeLangObj?.englishName || activeTranslationLang
                        }...`
                  }
                  className="w-full px-3 py-2 rounded-xl border border-slate-800 text-xs bg-[#0A0E17] text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
                <p className="text-[10px] text-slate-500">
                  Citizens completing the form in{" "}
                  {activeLangObj?.nativeName || activeTranslationLang} will see
                  this exact question prompt.
                </p>
              </div>
            );
          })()}
        </div>
      )}

      {/* Page & PDF Placement */}
      <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-800">
        <span>Page {fPage}</span>
        <span>{hasBbox ? "Placed on PDF" : "Not placed yet"}</span>
      </div>
    </div>
  );
}
