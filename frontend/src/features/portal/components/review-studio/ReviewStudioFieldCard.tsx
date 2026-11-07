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
import type { FormFieldItem } from "../../types";
import { CANONICAL_VAULT_KEYS, FIELD_TYPE_OPTIONS } from "./constants";

export interface ReviewStudioFieldCardProps {
  field: FormFieldItem;
  index: number;
  totalFields: number;
  canEdit: boolean;
  isHighlighted: boolean;
  sourceLanguage: string;
  supportedLanguages: string[];
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
      className={`p-4 rounded-xl border transition-all shadow-xs group cursor-pointer ${
        isHighlighted
          ? "border-[#6551f3] bg-indigo-50/20 ring-2 ring-[#6551f3]/30"
          : "border-slate-200 hover:border-blue-300 bg-white"
      }`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span
            className={`w-6 h-6 rounded-lg text-xs font-bold flex items-center justify-center ${
              isHighlighted
                ? "bg-[#6551f3] text-white"
                : "bg-slate-100 text-slate-600"
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
            className="text-sm font-bold text-slate-800 bg-transparent border-b border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-none px-1 py-0.5"
          />
        </div>

        <div className="flex items-center gap-1">
          {canEdit && (
            <>
              <button
                type="button"
                disabled={index === 0}
                onClick={(e) => {
                  e.stopPropagation();
                  onMoveField(index, "up");
                }}
                className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 disabled:opacity-20 ml-1 cursor-pointer"
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
                className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 disabled:opacity-20 cursor-pointer"
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
                className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 ml-1 cursor-pointer"
                title="Delete Field"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Field Parameters Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-slate-100">
        {/* Type */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-1">
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
          <label className="block text-[11px] font-semibold text-slate-500 mb-1">
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

        {/* Profile Vault Mapping */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-1">
            Profile Vault Pre-fill
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
              { value: "", label: "No prefill (custom field)" },
              ...CANONICAL_VAULT_KEYS.map((k) => ({
                value: k.key,
                label: k.label,
              })),
            ]}
            searchable
            searchPlaceholder="Search vault keys..."
            size="sm"
            aria-label="Profile Vault Pre-fill"
          />
        </div>
      </div>

      {/* Citizen Guidance Translations Toggle Bar */}
      <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setExpandedTranslationsFieldId(
              expandedTranslationsFieldId === field.id ? null : field.id
            );
          }}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition cursor-pointer"
        >
          <Globe className="w-3.5 h-3.5" />
          <span>Citizen Guidance Translations</span>
          <span className="text-[10px] bg-indigo-50 text-indigo-700 font-bold px-1.5 py-0.5 rounded-full border border-indigo-200">
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
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200/80 rounded-lg transition disabled:opacity-50 cursor-pointer"
            title="Auto-translate to all supported citizen guidance languages"
          >
            {translatingFieldId === field.id ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            )}
            <span>Auto-Translate All</span>
          </button>
        )}
      </div>

      {/* Expandable Multilingual Translations Drawer */}
      {expandedTranslationsFieldId === field.id && (
        <div
          className="mt-3 p-3 bg-slate-50/80 rounded-xl border border-slate-200 space-y-3"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Guidance Language for Citizens
            </span>
            <span className="text-[10px] text-slate-400">
              Original Form: {sourceLanguage.toUpperCase() || "DE"}
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
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition border cursor-pointer ${
                    isSelected
                      ? "bg-indigo-600 text-white border-indigo-600 shadow-2xs"
                      : "bg-white text-slate-700 border-slate-200 hover:bg-slate-100"
                  }`}
                >
                  <span>{label}</span>
                  {hasTranslation && (
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isSelected ? "bg-white" : "bg-emerald-500"
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
                  <label className="text-xs font-semibold text-slate-700">
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
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 disabled:opacity-50 cursor-pointer"
                    >
                      {translatingFieldId === field.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
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
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                <p className="text-[10px] text-slate-400">
                  Citizens completing the form in{" "}
                  {activeLangObj?.nativeName || activeTranslationLang} will see
                  this exact question prompt.
                </p>
              </div>
            );
          })()}
        </div>
      )}

      {/* Internal Technical Key */}
      <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-400 font-mono">
        <span>AcroForm Key: {field.key}</span>
        <span>Page {fPage}</span>
      </div>
    </div>
  );
}
