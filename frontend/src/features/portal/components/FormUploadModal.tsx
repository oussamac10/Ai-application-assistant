"use client";

import React, { useState } from "react";
import {
  UploadCloud,
  FileText,
  X,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Building2,
} from "lucide-react";
import { uploadOrganizationForm, listOrganizationCategories } from "../services/portalClient";
import { FormReviewDetail, OrganizationCategory } from "../types";
import { ModernSelect } from "@/components/ui/ModernSelect";

interface FormUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFormUploaded: (review: FormReviewDetail) => void;
}

export function FormUploadModal({
  isOpen,
  onClose,
  onFormUploaded,
}: FormUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [category, setCategory] = useState("general");
  const [selectedCategoryId, setSelectedCategoryId] = useState("");
  const [categories, setCategories] = useState<OrganizationCategory[]>([]);
  const [submissionMethod, setSubmissionMethod] = useState("print_and_sign");
  const [instructions, setInstructions] = useState("");
  const [requiredDocs, setRequiredDocs] = useState<string[]>([]);
  const [newDocInput, setNewDocInput] = useState("");
  const [autoExtract, setAutoExtract] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  React.useEffect(() => {
    if (isOpen) {
      listOrganizationCategories(true)
        .then((cats) => {
          setCategories(cats);
          if (cats.length > 0 && !selectedCategoryId) {
            setSelectedCategoryId(cats[0].id);
            setCategory(cats[0].slug);
          }
        })
        .catch(() => {});
    }
  }, [isOpen, selectedCategoryId]);

  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isUploading) {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isUploading, onClose]);

  if (!isOpen) return null;

  const handleFileChange = (selectedFile: File) => {
    const lowerName = selectedFile.name.toLowerCase();
    const isPdf =
      lowerName.endsWith(".pdf") ||
      selectedFile.type.toLowerCase() === "application/pdf";

    if (!isPdf) {
      setError("Only official PDF documents (.pdf) are supported.");
      return;
    }
    if (selectedFile.size > 25 * 1024 * 1024) {
      setError("File exceeds maximum allowed size of 25MB.");
      return;
    }
    setError(null);
    setFile(selectedFile);

    // Auto-generate name and key from filename if empty
    if (!name) {
      const cleanName = selectedFile.name
        .replace(/\.[^/.]+$/, "")
        .replace(/[-_]/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
      setName(cleanName);
    }
    if (!key) {
      const slug = selectedFile.name
        .replace(/\.[^/.]+$/, "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      setKey(slug);
    }
  };

  const handleAddDoc = () => {
    const trimmed = newDocInput.trim();
    if (trimmed && !requiredDocs.includes(trimmed)) {
      setRequiredDocs([...requiredDocs, trimmed]);
      setNewDocInput("");
    }
  };

  const handleRemoveDoc = (index: number) => {
    setRequiredDocs(requiredDocs.filter((_, idx) => idx !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please upload an official blank form PDF.");
      return;
    }
    if (!name.trim()) {
      setError("Please enter a title for this official form.");
      return;
    }

    try {
      setIsUploading(true);
      setError(null);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("name", name.trim());
      if (key.trim()) formData.append("key", key.trim());
      formData.append("category", category);
      if (selectedCategoryId) {
        formData.append("category_id", selectedCategoryId);
      }
      formData.append("submission_method", submissionMethod);
      if (instructions.trim()) formData.append("instructions", instructions.trim());
      formData.append("required_documents", JSON.stringify(requiredDocs));
      formData.append("auto_extract", String(autoExtract));

      const review = await uploadOrganizationForm(formData);
      onFormUploaded(review);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to upload and parse form";
      setError(message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Upload PDF Form"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#060910]/80 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div className="bg-[#0F1522] rounded-2xl shadow-2xl border border-white/10 text-slate-100 w-full max-w-2xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-white/10 flex items-center justify-between bg-[#0A0E17]/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center font-bold">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Upload PDF Form</h2>
              <p className="text-xs text-slate-400">
                Upload a blank PDF form to check its questions and layout.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isUploading}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-[#151D2E] transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-200 text-sm flex items-start gap-2.5">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Form Document Drag & Drop Zone */}
          <div>
            <label className="block text-xs font-semibold text-slate-200 mb-2">
              Official Blank PDF Document *
            </label>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragOver(false);
                if (e.dataTransfer.files?.[0]) {
                  handleFileChange(e.dataTransfer.files[0]);
                }
              }}
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all overflow-hidden ${
                isDragOver
                  ? "border-emerald-400 bg-emerald-500/10"
                  : file
                  ? "border-emerald-500/50 bg-emerald-500/10"
                  : "border-white/15 bg-[#0A0E17] hover:border-emerald-500/40 hover:bg-[#151D2E]/60"
              }`}
              onClick={() => document.getElementById("form-doc-input")?.click()}
            >
              <input
                id="form-doc-input"
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleFileChange(e.target.files[0]);
                }}
              />
              {file ? (
                <div className="flex items-center gap-3 min-w-0 max-w-full">
                  <FileText className="w-8 h-8 text-emerald-400 shrink-0" />
                  <div className="min-w-0 flex-1 text-left">
                    <p className="text-sm font-semibold text-white break-words line-clamp-2" title={file.name}>
                      {file.name}
                    </p>
                    <p className="text-xs text-slate-400">
                      {file.size < 1024
                        ? `${file.size} B`
                        : file.size < 1024 * 1024
                        ? `${(file.size / 1024).toFixed(1)} KB`
                        : `${(file.size / (1024 * 1024)).toFixed(2)} MB`}{" "}
                      • Ready for field extraction
                    </p>
                  </div>
                  <span className="ml-auto shrink-0 inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full text-emerald-300 bg-emerald-500/15 border border-emerald-500/30">
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                    PDF Attached
                  </span>
                </div>
              ) : (
                <div className="space-y-1.5">
                  <div className="mx-auto w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-2">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <p className="text-sm font-semibold text-slate-200">
                    Click to browse or drag and drop official form PDF
                  </p>
                  <p className="text-xs text-slate-400">
                    A4 standard municipal or institutional PDF (Max 25MB)
                  </p>
                </div>
              )}
            </div>

            {/* Auto-Extract Option */}
            <div className="mt-3 flex items-start gap-3 p-3 rounded-xl border border-white/10 bg-[#0A0E17]">
              <input
                id="auto-extract-toggle"
                type="checkbox"
                checked={autoExtract}
                onChange={(e) => setAutoExtract(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-white/20 bg-[#0F1522] text-emerald-500 focus:ring-emerald-500/30 accent-emerald-500 cursor-pointer"
              />
              <label htmlFor="auto-extract-toggle" className="text-xs cursor-pointer select-none">
                <span className="font-semibold text-slate-200">
                  Automatically detect form fields from document
                </span>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  Leave unchecked to start with a blank form and place fields manually on the canvas.
                </p>
              </label>
            </div>
          </div>

          {/* Form Title */}
          <div>
            <label className="block text-xs font-semibold text-slate-200 mb-1.5">
              Form Title *
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => {
                const val = e.target.value;
                const oldSlug = name
                  .toLowerCase()
                  .replace(/[^a-z0-9]+/g, "-")
                  .replace(/^-|-$/g, "");
                setName(val);
                if (!key || key === oldSlug) {
                  setKey(
                    val
                      .toLowerCase()
                      .replace(/[^a-z0-9]+/g, "-")
                      .replace(/^-|-$/g, "")
                  );
                }
              }}
              placeholder="e.g. Residence Registration Form"
              className="w-full px-3.5 py-2.5 rounded-xl border border-white/10 bg-[#0A0E17] text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>

          {/* Form Category (TYPO3-Inspired Taxonomy) */}
          <div>
            <label className="block text-xs font-semibold text-slate-200 mb-1.5">
              Official Category / Department
            </label>
            <ModernSelect
              value={selectedCategoryId}
              onChange={(catId) => {
                setSelectedCategoryId(catId);
                const found = categories.find((c) => c.id === catId);
                if (found) setCategory(found.slug);
                else if (!catId) setCategory("general");
              }}
              options={[
                { value: "", label: "General Administrative Services" },
                ...categories.map((c) => ({
                  value: c.id,
                  label: `${c.name}${c.translations?.en?.name ? ` (${c.translations.en.name})` : ""}`,
                })),
              ]}
              placeholder="Select official category..."
              searchable={categories.length > 5}
              searchPlaceholder="Search categories..."
              aria-label="Official Category / Department"
            />
          </div>

          {/* Instructions for Applicant */}
          <div>
            <label className="block text-xs font-semibold text-slate-200 mb-1.5">
              Official Instructions / Advice for Citizens
            </label>
            <textarea
              rows={2}
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g. Please ensure all personal and address information matches your official passport or identification."
              className="w-full px-3.5 py-2.5 rounded-xl border border-white/10 bg-[#0A0E17] text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>

          {/* Required Documents Checklist */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-semibold text-slate-200">
                Required Evidence / Documents Checklist
              </label>
              <span className="text-xs text-slate-400">
                Shown to citizens before completion
              </span>
            </div>
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
                className="flex-1 px-3.5 py-2 rounded-xl border border-white/10 bg-[#0A0E17] text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
              />
              <button
                type="button"
                onClick={handleAddDoc}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#151D2E] hover:bg-slate-800 border border-white/10 text-slate-200 text-xs font-medium transition-colors cursor-pointer"
              >
                <Plus className="w-4 h-4" /> Add Item
              </button>
            </div>
            <div className="space-y-1.5">
              {requiredDocs.map((doc, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#0A0E17] border border-white/10 text-xs text-slate-200"
                >
                  <span className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-[10px] font-bold flex items-center justify-center">
                      {idx + 1}
                    </span>
                    {doc}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleRemoveDoc(idx)}
                    className="text-slate-400 hover:text-rose-400 p-1 cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </form>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-white/10 flex items-center justify-between bg-[#0A0E17]/60">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Building2 className="w-4 h-4 text-slate-500" />
            <span>Scoped to organization workspace</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isUploading}
              className="px-4 py-2 text-sm text-slate-300 hover:text-white hover:bg-[#151D2E] rounded-xl font-medium transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={isUploading || !file}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading & Initializing Studio...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  Upload & Open Studio
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
