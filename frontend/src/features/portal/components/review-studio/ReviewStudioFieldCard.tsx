"use client";

import React from "react";
import {
  CheckSquare,
  ChevronDown,
  ChevronUp,
  Globe,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { ModernSelect } from "@/components/ui/ModernSelect";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import type {
  AutoMapFieldResult,
  FormFieldItem,
  FormFieldOptionBox,
  FormOptionItem,
} from "../../types";
import { CANONICAL_VAULT_KEYS, FIELD_TYPE_OPTIONS } from "./constants";

export interface ReviewStudioFieldCardProps {
  field: FormFieldItem;
  index: number;
  totalFields: number;
  canEdit: boolean;
  isHighlighted: boolean;
  isMultiSelected?: boolean;
  onToggleMultiSelect?: (fieldId: string) => void;
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
  isMultiSelected = false,
  onToggleMultiSelect,
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
  const rawOptionBoxes = field.configuration?.option_boxes;
  const optionBoxes = Array.isArray(rawOptionBoxes)
    ? (rawOptionBoxes as FormFieldOptionBox[])
    : [];
  const isLearnedPattern = Boolean(field.configuration?.learned_pattern_id);
  const isChoiceField =
    field.fieldType === "single_choice" ||
    field.fieldType === "multiple_choice" ||
    field.fieldType === "choice";

  const srcLang = sourceLanguage || "de";
  const getOptionLabel = (opt: FormOptionItem): string => {
    const srcT = opt.translations?.find((t) => t.language === srcLang)?.label;
    return srcT || opt.translations?.[0]?.label || opt.label || opt.value;
  };

  const handleUpdateOptionLabel = (optIdx: number, nextLabel: string) => {
    const updated = (field.options || []).map((opt, idx) => {
      if (idx !== optIdx) return opt;
      const existingTrans = [...(opt.translations || [])];
      const sIdx = existingTrans.findIndex((t) => t.language === srcLang);
      if (sIdx >= 0) {
        existingTrans[sIdx] = { ...existingTrans[sIdx], label: nextLabel };
      } else {
        existingTrans.push({ language: srcLang, label: nextLabel });
      }
      return {
        ...opt,
        label: nextLabel,
        translations: existingTrans,
      };
    });
    onFieldChange(field.id, { options: updated });
  };

  const handleAddOption = () => {
    const existing = field.options || [];
    const nextPos = existing.length + 1;
    const defaultLabel = `Option ${nextPos}`;
    const nextValue = `option_${nextPos}`;
    const updated: FormOptionItem[] = [
      ...existing,
      {
        value: nextValue,
        label: defaultLabel,
        position: nextPos,
        translations: [{ language: srcLang, label: defaultLabel }],
      },
    ];
    onFieldChange(field.id, { options: updated });
  };

  const handleRemoveOption = (optIdx: number) => {
    const updated = (field.options || [])
      .filter((_, idx) => idx !== optIdx)
      .map((opt, idx) => ({ ...opt, position: idx + 1 }));
    onFieldChange(field.id, { options: updated });
  };

  return (
    <div
      id={`field-card-${field.id}`}
      onClick={() => onSelectField(field.id, hasBbox ? fPage : undefined)}
      className={`p-4 rounded-xl border transition-all shadow-card group cursor-pointer ${
        isMultiSelected
          ? "border-sky-500/80 bg-sky-500/[0.06] ring-2 ring-sky-500/35"
          : isHighlighted
            ? "border-emerald-500/80 bg-emerald-500/[0.05] ring-2 ring-emerald-500/40 shadow-[0_0_12px_rgba(16,185,129,0.15)]"
            : "border-[var(--border-subtle)] hover:border-emerald-500/40 bg-[var(--bg-elevated)]"
      }`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {canEdit && onToggleMultiSelect && (
            <input
              type="checkbox"
              checked={isMultiSelected}
              onClick={(e) => e.stopPropagation()}
              onChange={() => onToggleMultiSelect(field.id)}
              aria-label={`Select ${primaryLabel}`}
              title="Select multiple fields to combine choices or group as a table row"
              className="h-4 w-4 rounded border-[var(--border-subtle)] accent-emerald-500 cursor-pointer shrink-0"
            />
          )}
          <span
            className={`w-6 h-6 rounded-lg text-xs font-mono font-bold flex items-center justify-center shrink-0 ${
              isHighlighted
                ? "bg-emerald-500 text-slate-950 shadow-2xs"
                : "bg-[var(--bg-muted)] text-[var(--text-secondary)] border border-[var(--border-subtle)]"
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
            className="text-sm font-bold text-[var(--text-primary)] bg-transparent border-b border-transparent hover:border-[var(--border-subtle)] focus:border-emerald-500 focus:outline-none px-1 py-0.5 w-full"
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
                className="p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-muted)] disabled:opacity-20 ml-1 cursor-pointer transition-colors"
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
                className="p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-muted)] disabled:opacity-20 cursor-pointer transition-colors"
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
                className="p-1 rounded text-[var(--text-muted)] hover:text-rose-500 hover:bg-rose-500/10 ml-1 cursor-pointer transition-colors"
                title="Delete Field"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Recognition & Option Box Badges */}
      {(optionBoxes.length > 0 || isLearnedPattern) && (
        <div className="flex flex-wrap items-center gap-1.5 mb-2.5">
          {optionBoxes.length > 0 && (
            <span className="inline-flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-300">
              <CheckSquare className="w-3 h-3" />
              <span>Linked to {optionBoxes.length} PDF checkboxes</span>
            </span>
          )}
          {isLearnedPattern && (
            <span className="inline-flex items-center gap-1 rounded-md border border-sky-500/30 bg-sky-500/10 px-2 py-0.5 text-[11px] font-medium text-sky-700 dark:text-sky-300">
              <Sparkles className="w-3 h-3" />
              <span>Recognized from past forms</span>
            </span>
          )}
        </div>
      )}

      {/* Field Parameters Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2.5 border-t border-[var(--border-subtle)]">
        {/* Type */}
        <div>
          <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1">
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
          <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1">
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
          <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1">
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
                <span className="text-emerald-700 dark:text-emerald-300 flex items-center gap-1 font-medium truncate mr-1">
                  <Sparkles className="w-3 h-3 text-emerald-500 dark:text-emerald-400 shrink-0" />
                  <span className="truncate">
                    Suggested: <span className="font-bold">{suggestedHumanLabel}</span> ({Math.round(autoMapSuggestion.confidence * 100)}%)
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

      {/* Inline Choice Options Editor */}
      {isChoiceField && (
        <div
          className="mt-3 pt-2.5 border-t border-[var(--border-subtle)] space-y-2"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[var(--text-secondary)]">
              Answer Choices ({field.options?.length || 0})
            </span>
            {canEdit && (
              <button
                type="button"
                onClick={handleAddOption}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 hover:underline cursor-pointer"
              >
                <Plus className="w-3 h-3" />
                <span>Add Option</span>
              </button>
            )}
          </div>
          {field.options && field.options.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {field.options.map((opt, optIdx) => (
                <div
                  key={`${opt.value}-${optIdx}`}
                  className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-muted)] px-2 py-1"
                >
                  <input
                    type="text"
                    disabled={!canEdit}
                    aria-label={`Choice option ${optIdx + 1}`}
                    value={getOptionLabel(opt)}
                    onChange={(e) =>
                      handleUpdateOptionLabel(optIdx, e.target.value)
                    }
                    className="bg-transparent text-xs font-medium text-[var(--text-primary)] focus:outline-none min-w-[60px] max-w-[140px]"
                  />
                  {canEdit && (
                    <button
                      type="button"
                      onClick={() => handleRemoveOption(optIdx)}
                      className="text-[var(--text-muted)] hover:text-rose-500 cursor-pointer p-0.5"
                      title="Remove option"
                      aria-label={`Remove option ${getOptionLabel(opt)}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Citizen Guidance Translations Toggle Bar */}
      <div className="mt-3 pt-2.5 border-t border-[var(--border-subtle)] flex items-center justify-between">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setExpandedTranslationsFieldId(
              expandedTranslationsFieldId === field.id ? null : field.id
            );
          }}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--text-secondary)] hover:text-emerald-600 dark:hover:text-emerald-400 cursor-pointer transition-colors"
        >
          <Globe className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />
          <span>Question Translations</span>
          <span className="text-[10px] bg-[var(--bg-muted)] text-emerald-600 dark:text-emerald-400 font-bold px-1.5 py-0.5 rounded-full border border-[var(--border-subtle)]">
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
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-lg transition disabled:opacity-50 cursor-pointer"
            title="Translate this question into all supported languages"
          >
            {translatingFieldId === field.id ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />
            )}
            <span>Translate All</span>
          </button>
        )}
      </div>

      {/* Expandable Multilingual Translations Drawer */}
      {expandedTranslationsFieldId === field.id && (
        <div
          className="mt-3 p-3 bg-[var(--bg-muted)] rounded-xl border border-[var(--border-subtle)] space-y-3"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[var(--text-secondary)]">
              Applicant Language
            </span>
            <span className="text-[10px] text-[var(--text-muted)] font-mono">
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
                      : "bg-[var(--bg-elevated)] text-[var(--text-secondary)] border-[var(--border-subtle)] hover:bg-[var(--bg-muted)]"
                  }`}
                >
                  <span>{label}</span>
                  {hasTranslation && (
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isSelected ? "bg-slate-950" : "bg-emerald-500"
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
                  <label className="text-xs font-semibold text-[var(--text-primary)]">
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
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 hover:underline disabled:opacity-50 cursor-pointer"
                    >
                      {translatingFieldId === field.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Sparkles className="w-3.5 h-3.5" />
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
                  className="w-full px-3 py-2 rounded-xl border border-[var(--border-subtle)] text-xs bg-[var(--bg-elevated)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
                <p className="text-[10px] text-[var(--text-muted)]">
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
      <div className="mt-2.5 flex items-center justify-between text-[11px] text-[var(--text-muted)] pt-2 border-t border-[var(--border-subtle)]">
        <span>Page {fPage}</span>
        <span>{hasBbox ? "Placed on PDF" : "Not placed yet"}</span>
      </div>
    </div>
  );
}
