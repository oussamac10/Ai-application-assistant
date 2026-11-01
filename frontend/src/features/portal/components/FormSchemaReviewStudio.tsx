"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  ArrowLeft,
  CheckCircle,
  FileText,
  Save,
  Plus,
  Trash2,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  Loader2,
  FolderArchive,
  Layers,
  Check,
  Crosshair,
  ZoomIn,
  ZoomOut,
  Target,
} from "lucide-react";
import {
  getFormReview,
  updateFormReview,
  updateFormField,
  addFormField,
  deleteFormField,
  reorderFormFields,
  publishForm,
  archiveForm,
  getFormPagePreviewUrl,
} from "../services/portalClient";
import { FormReviewDetail, FormFieldItem } from "../types";

interface FormSchemaReviewStudioProps {
  templateId: string;
  onBack: () => void;
  onPublished?: (updated: FormReviewDetail) => void;
  canEdit?: boolean;
}

const FIELD_TYPE_OPTIONS = [
  { value: "string", label: "Text / String" },
  { value: "date", label: "Date (ISO 8601)" },
  { value: "choice", label: "Choice / Dropdown / Radio" },
  { value: "number", label: "Number / Currency" },
  { value: "boolean", label: "Checkbox / Boolean" },
  { value: "signature", label: "Signature / Biometric Pad" },
];

const CANONICAL_VAULT_KEYS = [
  { key: "personal.first_name", label: "First Name (personal.first_name)" },
  { key: "personal.last_name", label: "Last Name (personal.last_name)" },
  { key: "personal.date_of_birth", label: "Date of Birth (personal.date_of_birth)" },
  { key: "personal.place_of_birth", label: "Place of Birth (personal.place_of_birth)" },
  { key: "personal.nationality", label: "Nationality (personal.nationality)" },
  { key: "contact.email", label: "Email Address (contact.email)" },
  { key: "contact.phone", label: "Phone Number (contact.phone)" },
  { key: "residence.street_and_number", label: "Street & Number / Anschrift (residence.street_and_number)" },
  { key: "residence.postal_code", label: "Postal Code (residence.postal_code)" },
  { key: "residence.city", label: "City (residence.city)" },
  { key: "residence.country", label: "Country (residence.country)" },
  { key: "financial.iban", label: "IBAN (financial.iban)" },
  { key: "residence.move_in_date", label: "Move-in Date (residence.move_in_date)" },
  { key: "signature.applicant", label: "Applicant Signature (signature.applicant)" },
];

export function FormSchemaReviewStudio({
  templateId,
  onBack,
  onPublished,
  canEdit = true,
}: FormSchemaReviewStudioProps) {
  const [review, setReview] = useState<FormReviewDetail | null>(null);
  const [fields, setFields] = useState<FormFieldItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form metadata states
  const [name, setName] = useState("");
  const [category, setCategory] = useState("general");
  const [submissionMethod, setSubmissionMethod] = useState("print_and_sign");
  const [instructions, setInstructions] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [activeTab, setActiveTab] = useState<"fields" | "metadata">("fields");

  // New field modal state
  const [showAddField, setShowAddField] = useState(false);
  const [addingField, setAddingField] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [newFieldKey, setNewFieldKey] = useState("");
  const [newFieldLabel, setNewFieldLabel] = useState("");
  const [newFieldType, setNewFieldType] = useState("string");
  const [newFieldRequired, setNewFieldRequired] = useState(true);
  const [newFieldQuestionKey, setNewFieldQuestionKey] = useState("");

  // Visual PDF inspection and placement states
  const [activePage, setActivePage] = useState(1);
  const [highlightedFieldId, setHighlightedFieldId] = useState<string | null>(null);
  const [isPlacingMode, setIsPlacingMode] = useState(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [dragCurrent, setDragCurrent] = useState<{ x: number; y: number } | null>(null);
  const [zoomScale, setZoomScale] = useState(1);
  const [newFieldBbox, setNewFieldBbox] = useState<[number, number, number, number] | null>(null);
  const [newFieldPage, setNewFieldPage] = useState<number>(1);
  const pdfContainerRef = useRef<HTMLDivElement>(null);
  const pdfImgRef = useRef<HTMLImageElement>(null);

  const loadReview = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getFormReview(templateId);
      setReview(data);
      setFields(data.fields || []);
      setName(data.name || "");
      setCategory(data.category || "general");
      setSubmissionMethod(data.submissionMethod || "print_and_sign");
      setInstructions(data.instructions || "");
      setReviewNotes(data.reviewNotes || "");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load form review schema";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [templateId]);

  useEffect(() => {
    loadReview();
  }, [loadReview]);

  const handleFieldChange = (
    fieldId: string,
    updates: Partial<FormFieldItem> & { label?: string; helpText?: string }
  ) => {
    setFields((prev) =>
      prev.map((f) => {
        if (f.id !== fieldId) return f;
        const updated = { ...f, ...updates };
        if (updates.label !== undefined) {
          const trans = [...(updated.translations || [])];
          if (trans.length > 0) {
            trans[0] = { ...trans[0], label: updates.label };
          } else {
            trans.push({ language: "de", label: updates.label });
          }
          updated.translations = trans;
        }
        return updated;
      })
    );
  };

  const handleSaveDraft = async () => {
    if (!review) return;
    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);

      // 1. Update metadata
      const updatedReview = await updateFormReview(templateId, {
        name: name.trim(),
        category,
        submissionMethod,
        instructions: instructions.trim(),
        reviewNotes: reviewNotes.trim(),
      });

      // 2. Persist fields
      for (const field of fields) {
        const trans = field.translations?.[0];
        await updateFormField(templateId, field.id, {
          key: field.key,
          label: trans?.label || field.key,
          fieldType: field.fieldType,
          requiredness: field.requiredness,
          questionKey: field.questionKey || null,
        });
      }

      // 3. Save order
      const orderedIds = fields.map((f) => f.id);
      await reorderFormFields(templateId, orderedIds);

      setReview(updatedReview);
      setSuccessMessage("Form schema draft saved successfully.");
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save draft schema";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleMoveField = (index: number, direction: "up" | "down") => {
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= fields.length) return;
    const copy = [...fields];
    const [moved] = copy.splice(index, 1);
    copy.splice(targetIndex, 0, moved);
    setFields(copy);
  };

  const handleDeleteField = async (fieldId: string) => {
    if (!confirm("Are you sure you want to remove this field from the schema?")) return;
    try {
      await deleteFormField(templateId, fieldId);
      setFields((prev) => prev.filter((f) => f.id !== fieldId));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete field";
      setError(msg);
    }
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isPlacingMode || !pdfImgRef.current) return;
    const rect = pdfImgRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setDragStart({ x, y });
    setDragCurrent({ x, y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isPlacingMode || !dragStart || !pdfImgRef.current) return;
    const rect = pdfImgRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, e.clientY - rect.top));
    setDragCurrent({ x, y });
  };

  const handleMouseUp = () => {
    if (!isPlacingMode || !dragStart || !dragCurrent || !pdfImgRef.current) return;
    const rect = pdfImgRef.current.getBoundingClientRect();
    const imgW = rect.width;
    const imgH = rect.height;

    let dispX0 = Math.min(dragStart.x, dragCurrent.x);
    let dispY0 = Math.min(dragStart.y, dragCurrent.y);
    let dispX1 = Math.max(dragStart.x, dragCurrent.x);
    let dispY1 = Math.max(dragStart.y, dragCurrent.y);

    // If single click (less than 10px), provide a standard fillable box
    if (Math.abs(dispX1 - dispX0) < 10 && Math.abs(dispY1 - dispY0) < 10) {
      dispX1 = Math.min(imgW - 10, dispX0 + Math.min(320, imgW * 0.7));
      dispY1 = dispY0 + 26;
    }

    const curPageDims = review?.pageDimensions?.find((p) => p.page === activePage) || {
      width: 595,
      height: 842,
    };
    const pdfX0 = Math.round((dispX0 / imgW) * curPageDims.width);
    const pdfY0 = Math.round((dispY0 / imgH) * curPageDims.height);
    const pdfX1 = Math.round((dispX1 / imgW) * curPageDims.width);
    const pdfY1 = Math.round((dispY1 / imgH) * curPageDims.height);

    setNewFieldBbox([pdfX0, pdfY0, pdfX1, pdfY1]);
    setNewFieldPage(activePage);
    setDragStart(null);
    setDragCurrent(null);
    setIsPlacingMode(false);
    setShowAddField(true);
  };

  const handleCreateField = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFieldLabel.trim()) return;
    try {
      setAddingField(true);
      setModalError(null);
      const created = await addFormField(templateId, {
        key: newFieldKey.trim() || newFieldLabel.toLowerCase().replace(/[^a-z0-9]+/g, "_"),
        label: newFieldLabel.trim(),
        fieldType: newFieldType,
        requiredness: newFieldRequired ? "required" : "optional",
        position: fields.length,
        questionKey: newFieldQuestionKey || null,
        configuration: {
          bbox: newFieldBbox || null,
          page: newFieldPage || activePage,
        },
        translations: [
          {
            language: review?.sourceLanguage || "de",
            label: newFieldLabel.trim(),
          },
        ],
      });
      setFields((prev) => [...prev, created]);
      setShowAddField(false);
      setNewFieldKey("");
      setNewFieldLabel("");
      setNewFieldType("string");
      setNewFieldRequired(true);
      setNewFieldQuestionKey("");
      setNewFieldBbox(null);
      setHighlightedFieldId(created.id);
      setSuccessMessage(`Field "${newFieldLabel.trim()}" added to schema.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to add new field";
      setModalError(msg);
      setError(msg);
    } finally {
      setAddingField(false);
    }
  };

  const handlePublish = async () => {
    if (!review) return;
    if (
      !confirm(
        `Are you ready to approve and publish "${name}" to the official portal catalog? Citizens will immediately be able to complete this form.`
      )
    ) {
      return;
    }

    try {
      setPublishing(true);
      setError(null);
      // Save changes first
      await handleSaveDraft();
      // Publish
      const published = await publishForm(templateId);
      setReview(published);
      setSuccessMessage("🎉 Form has been successfully approved and published to the Official Portal!");
      if (onPublished) onPublished(published);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to publish form";
      setError(msg);
    } finally {
      setPublishing(false);
    }
  };

  const handleArchive = async () => {
    if (!review) return;
    if (!confirm("Archive this form? It will no longer be visible in the citizen catalog.")) return;
    try {
      setSaving(true);
      const archived = await archiveForm(templateId);
      setReview(archived);
      setSuccessMessage("Form has been archived.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to archive form";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        <p className="text-sm font-medium text-slate-600">Loading form schema & coordinates...</p>
      </div>
    );
  }

  if (!review) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center">
        <AlertCircle className="w-12 h-12 text-red-500 mb-3" />
        <h3 className="text-lg font-bold text-slate-800">Form Not Found</h3>
        <p className="text-sm text-slate-500 mb-4">{error || "Unable to load review detail."}</p>
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium"
        >
          <ArrowLeft className="w-4 h-4" /> Return to Catalog
        </button>
      </div>
    );
  }

  const pdfUrl = `/api/organizations/current/forms/${templateId}/source-pdf`;

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] bg-slate-50">
      {/* Top Action Bar */}
      <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between shrink-0 shadow-sm">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 -ml-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
            title="Back to Catalog"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-base font-bold text-slate-900 truncate max-w-md">
                {name || review.name}
              </h1>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                  review.status === "published"
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                    : review.status === "archived"
                    ? "bg-slate-200 text-slate-700"
                    : "bg-amber-100 text-amber-800 border border-amber-200"
                }`}
              >
                {review.status === "published" ? "Live in Portal" : "Needs Review"}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                v{review.versionNumber} • {fields.length} Fields
              </span>
            </div>
            <p className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
              Verified Organization Schema • Dual-Pane Human Verification Studio
            </p>
          </div>
        </div>

        {/* Studio Actions */}
        <div className="flex items-center gap-3">
          {successMessage && (
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium">
              <Check className="w-3.5 h-3.5" />
              <span>{successMessage}</span>
            </div>
          )}
          {error && (
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs font-medium">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{error}</span>
            </div>
          )}

          {canEdit && (
            <>
              <button
                onClick={handleSaveDraft}
                disabled={saving || publishing}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save Draft
              </button>

              {review.status !== "published" && (
                <button
                  onClick={handlePublish}
                  disabled={saving || publishing}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
                >
                  {publishing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <CheckCircle className="w-4 h-4" />
                  )}
                  Approve & Publish to Portal
                </button>
              )}

              {review.status === "published" && (
                <button
                  onClick={handleArchive}
                  disabled={saving || publishing}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-600 text-xs font-medium transition-colors"
                >
                  <FolderArchive className="w-3.5 h-3.5" /> Archive
                </button>
              )}
            </>
          )}
        </div>
      </header>

      {/* Main Dual-Pane Studio Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Pane: Interactive Visual PDF Canvas & Placement Studio */}
        <div className="w-1/2 border-r border-slate-200 bg-slate-900 flex flex-col overflow-hidden">
          {/* Top Controls Toolbar */}
          <div className="px-4 py-2 bg-slate-800 border-b border-slate-700 flex items-center justify-between text-xs text-slate-300 font-medium shrink-0">
            {/* Page navigation */}
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white">Page</span>
              <div className="inline-flex items-center rounded-lg bg-slate-700 p-0.5 border border-slate-600">
                <button
                  type="button"
                  disabled={activePage <= 1}
                  onClick={() => setActivePage((p) => Math.max(1, p - 1))}
                  className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-600 disabled:opacity-30"
                  title="Previous Page"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <span className="px-2 text-xs font-mono font-bold text-white">
                  {activePage} / {review.pageCount || 1}
                </span>
                <button
                  type="button"
                  disabled={activePage >= (review.pageCount || 1)}
                  onClick={() => setActivePage((p) => Math.min(review.pageCount || 1, p + 1))}
                  className="p-1 rounded text-slate-300 hover:text-white hover:bg-slate-600 disabled:opacity-30"
                  title="Next Page"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Middle: Place Field on PDF */}
            {canEdit && (
              <button
                type="button"
                onClick={() => {
                  setIsPlacingMode(!isPlacingMode);
                  setDragStart(null);
                  setDragCurrent(null);
                }}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  isPlacingMode
                    ? "bg-[#6551f3] text-white shadow-md ring-2 ring-indigo-400"
                    : "bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-600"
                }`}
                title="Click and drag on the PDF to place an input box"
              >
                <Crosshair className="w-3.5 h-3.5" />
                <span>{isPlacingMode ? "Drawing Active (Click PDF)" : "+ Place Field on PDF"}</span>
              </button>
            )}

            {/* Right: Zoom & Open PDF */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setZoomScale((z) => Math.max(0.7, Math.round((z - 0.15) * 100) / 100))}
                className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="font-mono text-[11px] text-slate-400 w-10 text-center">
                {Math.round(zoomScale * 100)}%
              </span>
              <button
                type="button"
                onClick={() => setZoomScale((z) => Math.min(1.8, Math.round((z + 0.15) * 100) / 100))}
                className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <a
                href={pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white ml-1"
                title="Open PDF in New Window"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          {/* Interactive Mode Guidance Banner */}
          {isPlacingMode && (
            <div className="px-4 py-1.5 bg-[#6551f3] text-white text-[11px] font-semibold flex items-center justify-between shrink-0 shadow-inner">
              <span className="flex items-center gap-1.5">
                <Target className="w-3.5 h-3.5 animate-pulse" />
                Click and drag directly over any missing input box on the PDF below.
              </span>
              <button
                type="button"
                onClick={() => {
                  setIsPlacingMode(false);
                  setDragStart(null);
                  setDragCurrent(null);
                }}
                className="underline hover:no-underline text-[10px] font-bold"
              >
                Cancel
              </button>
            </div>
          )}

          {/* Canvas Viewport */}
          <div
            ref={pdfContainerRef}
            className="flex-1 overflow-auto p-4 flex items-start justify-center bg-slate-900"
          >
            <div
              className={`relative bg-white rounded shadow-2xl transition-transform origin-top ${
                isPlacingMode ? "cursor-crosshair ring-2 ring-[#6551f3]" : "cursor-default"
              }`}
              style={{
                transform: `scale(${zoomScale})`,
                width: "100%",
                maxWidth: "600px",
              }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                ref={pdfImgRef}
                src={getFormPagePreviewUrl(templateId, activePage)}
                alt={`Official PDF Page ${activePage}`}
                className="w-full h-auto block select-none pointer-events-none"
                draggable={false}
              />

              {/* Render field bounding boxes for active page */}
              {fields
                .map((field, idx) => ({ field, idx }))
                .filter(({ field }) => {
                  const fPage =
                    typeof field.configuration?.page === "number"
                      ? field.configuration.page
                      : 1;
                  return fPage === activePage && Array.isArray(field.configuration?.bbox);
                })
                .map(({ field, idx }) => {
                  const bbox = field.configuration.bbox as [number, number, number, number];
                  const curPageDims =
                    review.pageDimensions?.find((p) => p.page === activePage) || {
                      width: 595,
                      height: 842,
                    };
                  const topPct = (bbox[1] / curPageDims.height) * 100;
                  const leftPct = (bbox[0] / curPageDims.width) * 100;
                  const widthPct = ((bbox[2] - bbox[0]) / curPageDims.width) * 100;
                  const heightPct = ((bbox[3] - bbox[1]) / curPageDims.height) * 100;
                  const isHighlighted = highlightedFieldId === field.id;
                  const primaryLabel = field.translations?.[0]?.label || field.key;

                  return (
                    <div
                      key={field.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        setHighlightedFieldId(field.id);
                        document
                          .getElementById(`field-card-${field.id}`)
                          ?.scrollIntoView({ behavior: "smooth", block: "center" });
                      }}
                      style={{
                        top: `${topPct}%`,
                        left: `${leftPct}%`,
                        width: `${widthPct}%`,
                        height: `${heightPct}%`,
                      }}
                      className={`absolute rounded border-2 transition-all cursor-pointer flex items-start p-0.5 group ${
                        isHighlighted
                          ? "border-[#6551f3] bg-[#6551f3]/25 shadow-[0_0_0_3px_rgba(101,81,243,0.35)] z-20"
                          : "border-indigo-500/80 bg-indigo-500/15 hover:border-indigo-600 hover:bg-indigo-500/25 z-10"
                      }`}
                      title={`[${idx + 1}] ${primaryLabel} (Click to inspect in editor)`}
                    >
                      <span
                        className={`text-[9px] font-mono font-bold px-1 rounded shadow-xs truncate max-w-[130px] leading-tight ${
                          isHighlighted
                            ? "bg-[#6551f3] text-white"
                            : "bg-indigo-900/80 text-white group-hover:bg-indigo-600"
                        }`}
                      >
                        [{idx + 1}] {primaryLabel}
                      </span>
                    </div>
                  );
                })}

              {/* Active Drawing Dragging Box Indicator */}
              {isPlacingMode && dragStart && dragCurrent && (
                <div
                  style={{
                    top: `${Math.min(dragStart.y, dragCurrent.y)}px`,
                    left: `${Math.min(dragStart.x, dragCurrent.x)}px`,
                    width: `${Math.abs(dragCurrent.x - dragStart.x)}px`,
                    height: `${Math.abs(dragCurrent.y - dragStart.y)}px`,
                  }}
                  className="absolute border-2 border-dashed border-[#6551f3] bg-[#6551f3]/25 pointer-events-none z-30 flex items-center justify-center"
                >
                  <span className="bg-[#6551f3] text-white text-[9px] font-mono font-bold px-1 py-0.5 rounded shadow">
                    Placing New Input Box
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Pane: Schema Fields Editor & Review */}
        <div className="w-1/2 flex flex-col bg-white overflow-hidden">
          {/* Sub Navigation */}
          <div className="px-6 py-2 border-b border-slate-200 flex items-center justify-between bg-slate-50">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setActiveTab("fields")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === "fields"
                    ? "bg-white text-blue-700 shadow-sm border border-slate-200"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <Layers className="w-3.5 h-3.5" /> Form Fields Schema ({fields.length})
              </button>
              <button
                onClick={() => setActiveTab("metadata")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                  activeTab === "metadata"
                    ? "bg-white text-blue-700 shadow-sm border border-slate-200"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                <FileText className="w-3.5 h-3.5" /> General Details & Rules
              </button>
            </div>

            {activeTab === "fields" && canEdit && (
              <button
                onClick={() => setShowAddField(true)}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-semibold transition-colors"
              >
                <Plus className="w-3.5 h-3.5" /> Add Field
              </button>
            )}
          </div>

          {/* Editor Content Area */}
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === "fields" ? (
              <div className="space-y-4">
                <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-100 text-blue-900 text-xs flex items-start gap-2.5">
                  <Sparkles className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold">AcroForm Widgets & Profile Vault Mapping:</span>
                    <p className="text-blue-800 text-[11px] mt-0.5">
                      Verify each question label and select its canonical profile vault key. Citizens with existing encrypted vaults will be able to complete mapped fields with a single click.
                    </p>
                  </div>
                </div>

                {fields.length === 0 ? (
                  <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-2xl">
                    <FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                    <p className="text-sm font-semibold text-slate-700">No fields extracted</p>
                    <p className="text-xs text-slate-400 mt-1 mb-4">
                      Add questions manually to configure this form.
                    </p>
                    {canEdit && (
                      <button
                        onClick={() => setShowAddField(true)}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold"
                      >
                        <Plus className="w-4 h-4" /> Add First Field
                      </button>
                    )}
                  </div>
                ) : (
                  fields.map((field, idx) => {
                    const primaryLabel =
                      field.translations?.[0]?.label || field.key;
                    const isRequired = field.requiredness === "required" || field.required;
                    const isHighlighted = highlightedFieldId === field.id;
                    const fPage =
                      typeof field.configuration?.page === "number"
                        ? field.configuration.page
                        : 1;
                    const hasBbox = Array.isArray(field.configuration?.bbox);

                    return (
                      <div
                        key={field.id}
                        id={`field-card-${field.id}`}
                        onClick={() => setHighlightedFieldId(field.id)}
                        className={`p-4 rounded-xl border transition-all shadow-xs group ${
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
                              {idx + 1}
                            </span>
                            <input
                              type="text"
                              disabled={!canEdit}
                              value={primaryLabel}
                              onChange={(e) =>
                                handleFieldChange(field.id, { label: e.target.value })
                              }
                              className="text-sm font-bold text-slate-800 bg-transparent border-b border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-none px-1 py-0.5"
                            />
                          </div>

                          <div className="flex items-center gap-1">
                            {hasBbox && (
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActivePage(fPage);
                                  setHighlightedFieldId(field.id);
                                }}
                                className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 transition-colors"
                                title="Focus this box on the PDF canvas"
                              >
                                <Target className="w-3 h-3" /> Focus Box
                              </button>
                            )}
                            {canEdit && (
                              <>
                                <button
                                  type="button"
                                  disabled={idx === 0}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleMoveField(idx, "up");
                                  }}
                                  className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 disabled:opacity-20 ml-1"
                                  title="Move Up"
                                >
                                  <ChevronUp className="w-4 h-4" />
                                </button>
                                <button
                                  type="button"
                                  disabled={idx === fields.length - 1}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleMoveField(idx, "down");
                                  }}
                                  className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 disabled:opacity-20"
                                  title="Move Down"
                                >
                                  <ChevronDown className="w-4 h-4" />
                                </button>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteField(field.id);
                                  }}
                                  className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 ml-1"
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
                            <select
                              disabled={!canEdit}
                              value={field.fieldType}
                              onChange={(e) =>
                                handleFieldChange(field.id, { fieldType: e.target.value })
                              }
                              className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            >
                              {FIELD_TYPE_OPTIONS.map((opt) => (
                                <option key={opt.value} value={opt.value}>
                                  {opt.label}
                                </option>
                              ))}
                            </select>
                          </div>

                          {/* Requirement */}
                          <div>
                            <label className="block text-[11px] font-semibold text-slate-500 mb-1">
                              Requirement
                            </label>
                            <select
                              disabled={!canEdit}
                              value={isRequired ? "required" : "optional"}
                              onChange={(e) =>
                                handleFieldChange(field.id, {
                                  requiredness: e.target.value,
                                  required: e.target.value === "required",
                                })
                              }
                              className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            >
                              <option value="required">Required for Citizen</option>
                              <option value="optional">Optional</option>
                            </select>
                          </div>

                          {/* Profile Vault Mapping */}
                          <div>
                            <label className="block text-[11px] font-semibold text-slate-500 mb-1">
                              Profile Vault Pre-fill
                            </label>
                            <select
                              disabled={!canEdit}
                              value={field.questionKey || ""}
                              onChange={(e) =>
                                handleFieldChange(field.id, {
                                  questionKey: e.target.value || null,
                                })
                              }
                              className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            >
                              <option value="">No prefill (custom field)</option>
                              {CANONICAL_VAULT_KEYS.map((k) => (
                                <option key={k.key} value={k.key}>
                                  {k.label}
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>

                        {/* Internal Technical Key */}
                        <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-400 font-mono">
                          <span>AcroForm Key: {field.key}</span>
                          <span>Page {fPage}</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            ) : (
              /* General Metadata Tab */
              <div className="space-y-5">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Official Form Title *
                  </label>
                  <input
                    type="text"
                    disabled={!canEdit}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Official Guidance & Instructions for Citizen
                  </label>
                  <textarea
                    rows={3}
                    disabled={!canEdit}
                    value={instructions}
                    onChange={(e) => setInstructions(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Internal Verification & Audit Notes
                  </label>
                  <textarea
                    rows={2}
                    disabled={!canEdit}
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="e.g. Verified by Form Officer Marcus Weber against official Baden-Württemberg 2026 guidelines."
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Add Field Modal */}
      {showAddField && (
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

            {newFieldBbox && (
              <div className="p-2.5 rounded-xl bg-indigo-50/70 border border-indigo-100 text-indigo-900 text-xs flex items-center justify-between">
                <span className="font-medium text-[11px]">
                  Coordinates: [X: {Math.round(newFieldBbox[0])}, Y: {Math.round(newFieldBbox[1])}, W: {Math.round(newFieldBbox[2] - newFieldBbox[0])}, H: {Math.round(newFieldBbox[3] - newFieldBbox[1])}] pt
                </span>
                <button
                  type="button"
                  onClick={() => setNewFieldBbox(null)}
                  className="text-[10px] text-indigo-600 hover:text-indigo-800 underline font-medium"
                >
                  Clear Box
                </button>
              </div>
            )}

            {modalError && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleCreateField} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Question Label *
                </label>
                <input
                  type="text"
                  required
                  value={newFieldLabel}
                  onChange={(e) => {
                    setNewFieldLabel(e.target.value);
                    if (!newFieldKey) {
                      setNewFieldKey(
                        e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, "_")
                      );
                    }
                  }}
                  placeholder="e.g. Vorname / First Name"
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
                  <select
                    value={newFieldType}
                    onChange={(e) => setNewFieldType(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {FIELD_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Requirement
                  </label>
                  <select
                    value={newFieldRequired ? "yes" : "no"}
                    onChange={(e) => setNewFieldRequired(e.target.value === "yes")}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="yes">Required</option>
                    <option value="no">Optional</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Profile Vault Pre-fill Mapping
                </label>
                <select
                  value={newFieldQuestionKey}
                  onChange={(e) => setNewFieldQuestionKey(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">None (custom)</option>
                  {CANONICAL_VAULT_KEYS.map((k) => (
                    <option key={k.key} value={k.key}>
                      {k.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  disabled={addingField}
                  onClick={() => {
                    setShowAddField(false);
                    setNewFieldBbox(null);
                    setModalError(null);
                  }}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-800 font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingField || !newFieldLabel.trim()}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold disabled:opacity-50"
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
      )}
    </div>
  );
}
