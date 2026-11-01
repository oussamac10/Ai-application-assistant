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
import { uploadOrganizationForm } from "../services/portalClient";
import { FormReviewDetail } from "../types";

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
  const [submissionMethod, setSubmissionMethod] = useState("print_and_sign");
  const [instructions, setInstructions] = useState("");
  const [requiredDocs, setRequiredDocs] = useState<string[]>([]);
  const [newDocInput, setNewDocInput] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  if (!isOpen) return null;

  const handleFileChange = (selectedFile: File) => {
    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select an official PDF document (.pdf).");
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
      setError("Please upload an official PDF form file.");
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
      formData.append("submission_method", submissionMethod);
      if (instructions.trim()) formData.append("instructions", instructions.trim());
      formData.append("required_documents", JSON.stringify(requiredDocs));

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Upload & Ingest Official Form</h2>
              <p className="text-xs text-slate-500">
                AI and AcroForm extraction will parse fields, extract coordinates, and build the multilingual review schema.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isUploading}
            className="text-slate-400 hover:text-slate-600 p-2 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-start gap-2.5">
              <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* PDF Drag & Drop Zone */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
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
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                isDragOver
                  ? "border-blue-500 bg-blue-50/50"
                  : file
                  ? "border-emerald-400 bg-emerald-50/30"
                  : "border-slate-200 hover:border-blue-400 hover:bg-slate-50"
              }`}
              onClick={() => document.getElementById("form-pdf-input")?.click()}
            >
              <input
                id="form-pdf-input"
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleFileChange(e.target.files[0]);
                }}
              />
              {file ? (
                <div className="flex items-center justify-center gap-3">
                  <FileText className="w-8 h-8 text-emerald-600 shrink-0" />
                  <div className="text-left">
                    <p className="text-sm font-semibold text-slate-800">{file.name}</p>
                    <p className="text-xs text-slate-500">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for field extraction
                    </p>
                  </div>
                  <span className="ml-auto inline-flex items-center text-xs font-medium text-emerald-700 bg-emerald-100 px-2.5 py-1 rounded-full">
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> PDF Attached
                  </span>
                </div>
              ) : (
                <div className="space-y-1.5">
                  <div className="mx-auto w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mb-2">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <p className="text-sm font-semibold text-slate-700">
                    Click to browse or drag and drop official form PDF
                  </p>
                  <p className="text-xs text-slate-400">
                    A4 standard municipal PDF with AcroForm widgets or printable tables (Max 25MB)
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Form Title & Key */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Official Form Title *
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Residence Registration Form"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Internal Identifier / Key
              </label>
              <input
                type="text"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="e.g. residence-registration-form"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800 font-mono text-xs"
              />
            </div>
          </div>

          {/* Instructions for Applicant */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Official Instructions / Advice for Citizens
            </label>
            <textarea
              rows={2}
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g. Please ensure all personal and address information matches your official passport or identification."
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
            />
          </div>

          {/* Required Documents Checklist */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-semibold text-slate-700">
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
                className="flex-1 px-3.5 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
              />
              <button
                type="button"
                onClick={handleAddDoc}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors"
              >
                <Plus className="w-4 h-4" /> Add Item
              </button>
            </div>
            <div className="space-y-1.5">
              {requiredDocs.map((doc, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700"
                >
                  <span className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold flex items-center justify-center">
                      {idx + 1}
                    </span>
                    {doc}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleRemoveDoc(idx)}
                    className="text-slate-400 hover:text-red-500 p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </form>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <Building2 className="w-4 h-4 text-slate-400" />
            <span>Scoped to organization workspace</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isUploading}
              className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800 font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={isUploading || !file}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Extracting Fields & Building Schema...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  Parse & Launch Review Studio
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
