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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs">
      <div className="bg-[#0F1522] rounded-2xl shadow-panel border border-slate-800 w-full max-w-md p-6 space-y-4 text-slate-100">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-white">Add a New Question</h3>
          {newFieldBbox && (
            <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[11px] font-semibold flex items-center gap-1">
              <Target className="w-3 h-3 text-emerald-400" /> Placed on Page {newFieldPage}
            </span>
          )}
        </div>

        {/* PDF Placement Card */}
        <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 text-xs flex items-center justify-between">
          <div>
            <span className="font-semibold text-xs flex items-center gap-1.5 text-white">
              <Target className="w-3.5 h-3.5 text-emerald-400" />
              PDF Position: Page {newFieldPage}
            </span>
            {newFieldBbox ? (
              <p className="text-[11px] text-emerald-400 mt-0.5">
                Position selected on Page {newFieldPage}
              </p>
            ) : (
              <p className="text-[11px] text-slate-400 mt-0.5">
                Click &apos;Pick on PDF&apos; to choose where this answer goes.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onPickOnPdf}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold shadow-xs transition-colors shrink-0 ml-2 cursor-pointer"
            title="Click or drag directly on the PDF to choose where this field goes"
          >
            <Crosshair className="w-3.5 h-3.5" />
            {newFieldBbox ? "Change on PDF" : "Pick on PDF"}
          </button>
        </div>

        {modalError && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{modalError}</span>
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
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
              className="w-full px-3 py-2 rounded-xl border border-slate-800 bg-[#0A0E17] text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
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
              <label className="block text-xs font-semibold text-slate-300 mb-1">
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
            <label className="block text-xs font-semibold text-slate-300 mb-1">
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

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              disabled={addingField}
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-white font-medium disabled:opacity-50 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={addingField || !newFieldLabel.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold disabled:opacity-50 cursor-pointer transition-colors"
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
