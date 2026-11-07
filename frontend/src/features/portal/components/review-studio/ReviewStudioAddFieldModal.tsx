"use client";

import React from "react";
import { AlertCircle, Crosshair, Loader2, Target } from "lucide-react";
import { ModernSelect } from "@/components/ui/ModernSelect";
import { FIELD_TYPE_OPTIONS, CANONICAL_VAULT_KEYS } from "./constants";

export interface ReviewStudioAddFieldModalProps {
  showAddField: boolean;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => void;
  addingField: boolean;
  modalError: string | null;
  newFieldLabel: string;
  setNewFieldLabel: (val: string) => void;
  newFieldKey: string;
  setNewFieldKey: (val: string) => void;
  newFieldType: string;
  setNewFieldType: (val: string) => void;
  newFieldRequired: boolean;
  setNewFieldRequired: (val: boolean) => void;
  newFieldQuestionKey: string;
  setNewFieldQuestionKey: (val: string) => void;
  newFieldBbox: [number, number, number, number] | null;
  newFieldPage: number;
  onPickOnPdf: () => void;
}

export function ReviewStudioAddFieldModal({
  showAddField,
  onClose,
  onSubmit,
  addingField,
  modalError,
  newFieldLabel,
  setNewFieldLabel,
  newFieldKey,
  setNewFieldKey,
  newFieldType,
  setNewFieldType,
  newFieldRequired,
  setNewFieldRequired,
  newFieldQuestionKey,
  setNewFieldQuestionKey,
  newFieldBbox,
  newFieldPage,
  onPickOnPdf,
}: ReviewStudioAddFieldModalProps) {
  if (!showAddField) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-md p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-slate-900">Add Field to Form Schema</h3>
          {newFieldBbox && (
            <span className="px-2 py-0.5 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-[10px] font-mono font-semibold flex items-center gap-1">
              <Target className="w-3 h-3 text-indigo-600" /> Page {newFieldPage} Box Placed
            </span>
          )}
        </div>

        {/* PDF Placement Card */}
        <div className="p-3 rounded-xl bg-indigo-50/80 border border-indigo-100 text-indigo-900 text-xs flex items-center justify-between">
          <div>
            <span className="font-semibold text-xs flex items-center gap-1.5 text-indigo-900">
              <Target className="w-3.5 h-3.5 text-indigo-600" />
              PDF Position: Page {newFieldPage}
            </span>
            {newFieldBbox ? (
              <p className="text-[11px] text-indigo-600 font-mono mt-0.5">
                X: {Math.round(newFieldBbox[0])}, Y: {Math.round(newFieldBbox[1])}, W: {Math.round(newFieldBbox[2] - newFieldBbox[0])}, H: {Math.round(newFieldBbox[3] - newFieldBbox[1])} pt
              </p>
            ) : (
              <p className="text-[11px] text-indigo-500 mt-0.5">
                Click &apos;Pick on PDF&apos; to choose where this field goes.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onPickOnPdf}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors shrink-0 ml-2 cursor-pointer"
            title="Click or drag directly on the PDF to choose where this field goes"
          >
            <Crosshair className="w-3.5 h-3.5" />
            {newFieldBbox ? "Change on PDF" : "Pick on PDF"}
          </button>
        </div>

        {modalError && (
          <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{modalError}</span>
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Question Label *
            </label>
            <input
              type="text"
              required
              value={newFieldLabel}
              onChange={(e) => {
                const val = e.target.value;
                const oldSlug = newFieldLabel.toLowerCase().replace(/[^a-z0-9]+/g, "_");
                setNewFieldLabel(val);
                if (!newFieldKey || newFieldKey === oldSlug) {
                  setNewFieldKey(val.toLowerCase().replace(/[^a-z0-9]+/g, "_"));
                }
              }}
              placeholder="e.g. First Name / Given Name"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Technical Identifier / Key
            </label>
            <input
              type="text"
              value={newFieldKey}
              onChange={(e) => setNewFieldKey(e.target.value)}
              placeholder="e.g. applicant_first_name"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Input Type
              </label>
              <ModernSelect
                value={newFieldType}
                onChange={(val) => setNewFieldType(val)}
                options={FIELD_TYPE_OPTIONS}
                size="sm"
                aria-label="Input Type"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Requirement
              </label>
              <ModernSelect
                value={newFieldRequired ? "yes" : "no"}
                onChange={(val) => setNewFieldRequired(val === "yes")}
                options={[
                  { value: "yes", label: "Required" },
                  { value: "no", label: "Optional" },
                ]}
                size="sm"
                aria-label="Requirement"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Profile Vault Pre-fill Mapping
            </label>
            <ModernSelect
              value={newFieldQuestionKey}
              onChange={(val) => setNewFieldQuestionKey(val)}
              options={[
                { value: "", label: "None (custom)" },
                ...CANONICAL_VAULT_KEYS.map((k) => ({
                  value: k.key,
                  label: k.label,
                })),
              ]}
              searchable
              searchPlaceholder="Search vault keys..."
              size="sm"
              aria-label="Profile Vault Pre-fill Mapping"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              disabled={addingField}
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-800 font-medium disabled:opacity-50 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={addingField || !newFieldLabel.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold disabled:opacity-50 cursor-pointer"
            >
              {addingField ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Adding Field...
                </>
              ) : (
                "Add Field"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
