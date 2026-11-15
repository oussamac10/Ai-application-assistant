"use client";

import React from "react";
import { Plus, Trash2 } from "lucide-react";
import { ModernSelect } from "@/components/ui/ModernSelect";
import type { OrganizationCategory } from "../../types";

export interface ReviewStudioMetadataTabProps {
  canEdit: boolean;
  name: string;
  setName: (val: string) => void;
  category: string;
  setCategory: (val: string) => void;
  categoryId: string | null;
  setCategoryId: (val: string | null) => void;
  availableCategories: OrganizationCategory[];
  instructions: string;
  setInstructions: (val: string) => void;
  requiredDocs: string[];
  newDocInput: string;
  setNewDocInput: (val: string) => void;
  handleAddDoc: () => void;
  handleRemoveDoc: (idx: number) => void;
  reviewNotes: string;
  setReviewNotes: (val: string) => void;
}

export function ReviewStudioMetadataTab({
  canEdit,
  name,
  setName,
  setCategory,
  categoryId,
  setCategoryId,
  availableCategories,
  instructions,
  setInstructions,
  requiredDocs,
  newDocInput,
  setNewDocInput,
  handleAddDoc,
  handleRemoveDoc,
  reviewNotes,
  setReviewNotes,
}: ReviewStudioMetadataTabProps) {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
          Official Form Title *
        </label>
        <input
          type="text"
          disabled={!canEdit}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-3.5 py-2.5 rounded-xl border border-slate-800 bg-[#0F1522] text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
          Official Category / Department (Taxonomy)
        </label>
        <ModernSelect
          disabled={!canEdit}
          value={categoryId || ""}
          onChange={(val) => {
            setCategoryId(val || null);
            const found = availableCategories.find((c) => c.id === val);
            if (found) setCategory(found.slug);
            else if (!val) setCategory("general");
          }}
          options={[
            { value: "", label: "Uncategorized / General Services" },
            ...availableCategories.map((c) => ({
              value: c.id,
              label: `${c.name}${c.translations?.en?.name ? ` (${c.translations.en.name})` : ""}`,
            })),
          ]}
          placeholder="Select category..."
          searchable={availableCategories.length > 5}
          searchPlaceholder="Search categories..."
          aria-label="Official Category / Department"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
          Official Guidance & Instructions for Citizen
        </label>
        <textarea
          rows={3}
          disabled={!canEdit}
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          placeholder="e.g. Please ensure all personal and address information matches your official passport or identification."
          className="w-full px-3.5 py-2.5 rounded-xl border border-slate-800 bg-[#0F1522] text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
      </div>

      {/* Required Documents / Evidence Checklist */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-xs font-semibold text-slate-300">
            Required Evidence / Documents Checklist
          </label>
          <span className="text-xs text-slate-500 font-mono">
            Shown to citizens before starting application
          </span>
        </div>

        {canEdit && (
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newDocInput}
              onChange={(e) => setNewDocInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddDoc();
                }
              }}
              placeholder="e.g. Valid Passport, Identity Card, or Proof of Address"
              className="flex-1 px-3.5 py-2 rounded-xl border border-slate-800 bg-[#0F1522] text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500 text-white placeholder-slate-500"
            />
            <button
              type="button"
              onClick={handleAddDoc}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors cursor-pointer"
            >
              <Plus className="w-4 h-4" /> Add Item
            </button>
          </div>
        )}

        {requiredDocs.length === 0 ? (
          <p className="text-xs text-slate-500 italic py-2">
            No required evidence documents added yet.
          </p>
        ) : (
          <div className="space-y-1.5">
            {requiredDocs.map((doc, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#0F1522] border border-slate-800 text-xs text-slate-200"
              >
                <span className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-slate-800 text-emerald-400 text-[10px] font-mono font-bold flex items-center justify-center shrink-0 border border-slate-700">
                    {idx + 1}
                  </span>
                  <span>{doc}</span>
                </span>
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => handleRemoveDoc(idx)}
                    className="text-slate-500 hover:text-red-400 p-1 cursor-pointer transition-colors"
                    title="Remove item"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
          Internal Verification & Audit Notes
        </label>
        <textarea
          rows={2}
          disabled={!canEdit}
          value={reviewNotes}
          onChange={(e) => setReviewNotes(e.target.value)}
          placeholder="e.g. Verified by Review Officer against official guidelines."
          className="w-full px-3.5 py-2.5 rounded-xl border border-slate-800 bg-[#0F1522] text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
      </div>
    </div>
  );
}
