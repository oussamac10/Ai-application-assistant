"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
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
  clearFormFields,
  deleteForm,
  reorderFormFields,
  autoDetectFormFields,
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
  const [autoDetecting, setAutoDetecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form metadata states
  const [name, setName] = useState("");
  const [category, setCategory] = useState("general");
  const [submissionMethod, setSubmissionMethod] = useState("print_and_sign");
  const [instructions, setInstructions] = useState("");
  const [requiredDocs, setRequiredDocs] = useState<string[]>([]);
  const [newDocInput, setNewDocInput] = useState("");
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
  const [zoomScale, setZoomScale] = useState(1);
  const [newFieldBbox, setNewFieldBbox] = useState<[number, number, number, number] | null>(null);
  const [newFieldPage, setNewFieldPage] = useState<number>(1);
  const [pickingFieldForLocation, setPickingFieldForLocation] = useState<"new" | string | null>(null);
  const pdfContainerRef = useRef<HTMLDivElement>(null);
  const pdfImgRef = useRef<HTMLImageElement>(null);

  // Calculates a smart default box on the PDF page (below existing fields or centered)
  const computeDefaultBbox = (
    allFields: FormFieldItem[],
    page: number,
    dims: { width: number; height: number }
  ): [number, number, number, number] => {
    const pageFields = allFields.filter((f) => {
      const fPage = typeof f.configuration?.page === "number" ? f.configuration.page : 1;
      return fPage === page && Array.isArray(f.configuration?.bbox);
    });

    if (pageFields.length > 0) {
      const maxY1 = Math.max(
        ...pageFields.map((f) => (f.configuration.bbox as [number, number, number, number])[3])
      );
      const nextY0 = Math.min(dims.height - 45, maxY1 + 18);
      const nextY1 = Math.min(dims.height - 15, nextY0 + 26);
      return [
        55,
        Math.round(nextY0 * 10) / 10,
        Math.round((dims.width - 55) * 10) / 10,
        Math.round(nextY1 * 10) / 10,
      ];
    }
    return [55, 120, Math.round((dims.width - 55) * 10) / 10, 146];
  };

  // Active interaction: drawing a new box, moving an existing box, or resizing an existing box
  type InteractionType = "draw" | "move" | "resize";
  type ResizeHandle = "nw" | "ne" | "se" | "sw" | "e" | "s";

  const [interaction, setInteraction] = useState<{
    type: InteractionType;
    fieldId?: string;
    handle?: ResizeHandle;
    initialBbox?: [number, number, number, number];
    startClientX: number;
    startClientY: number;
    currentClientX: number;
    currentClientY: number;
  } | null>(null);

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
      setRequiredDocs(data.requiredDocuments || []);
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

  const handleAutoDetect = async () => {
    try {
      setAutoDetecting(true);
      setError(null);
      const updated = await autoDetectFormFields(templateId);
      setReview(updated);
      setFields(updated.fields || []);
      setSuccessMessage(
        updated.fields?.length
          ? `Successfully detected ${updated.fields.length} fields from document.`
          : "No interactive fields detected. You can place fields manually on the canvas."
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to auto-detect fields";
      setError(msg);
    } finally {
      setAutoDetecting(false);
    }
  };

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
        requiredDocuments: requiredDocs,
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

  const handleDeleteField = useCallback(async (fieldId: string) => {
    if (!confirm("Are you sure you want to remove this field from the schema?")) return;
    try {
      await deleteFormField(templateId, fieldId);
      setFields((prev) => prev.filter((f) => f.id !== fieldId));
      if (highlightedFieldId === fieldId) {
        setHighlightedFieldId(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete field";
      setError(msg);
    }
  }, [templateId, highlightedFieldId]);

  const handleDeleteForm = async () => {
    if (!confirm("Are you sure you want to permanently delete this official form template? This action cannot be undone.")) {
      return;
    }
    try {
      setSaving(true);
      await deleteForm(templateId);
      onBack();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete form";
      setError(msg);
      setSaving(false);
    }
  };

  const handleClearAllFields = async () => {
    if (!confirm("Are you sure you want to delete all fields from this form? You can then start completely clean.")) {
      return;
    }
    try {
      setSaving(true);
      const updated = await clearFormFields(templateId);
      setReview(updated);
      setFields([]);
      setHighlightedFieldId(null);
      setSuccessMessage("All fields cleared.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to clear fields";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!highlightedFieldId || !canEdit) return;
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }
      if (e.key === "Delete" || e.key === "Backspace") {
        e.preventDefault();
        handleDeleteField(highlightedFieldId);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [highlightedFieldId, canEdit, handleDeleteField]);

  // Window-level listener for live dragging (moving existing box, resizing, or drawing new box)
  useEffect(() => {
    if (!interaction) return;

    const handleWindowMouseMove = (e: MouseEvent) => {
      if (!pdfImgRef.current || !review) return;
      const rect = pdfImgRef.current.getBoundingClientRect();
      const curPageDims = review.pageDimensions?.find((p) => p.page === activePage) || {
        width: 595,
        height: 842,
      };
      const scaleX = curPageDims.width / rect.width;
      const scaleY = curPageDims.height / rect.height;

      const deltaXPt = (e.clientX - interaction.startClientX) * scaleX;
      const deltaYPt = (e.clientY - interaction.startClientY) * scaleY;

      if (interaction.type === "draw") {
        setInteraction((prev) =>
          prev ? { ...prev, currentClientX: e.clientX, currentClientY: e.clientY } : null
        );
      } else if (interaction.type === "move" && interaction.fieldId && interaction.initialBbox) {
        const [x0, y0, x1, y1] = interaction.initialBbox;
        const w = x1 - x0;
        const h = y1 - y0;
        const newX0 = Math.max(0, Math.min(curPageDims.width - w, x0 + deltaXPt));
        const newY0 = Math.max(0, Math.min(curPageDims.height - h, y0 + deltaYPt));
        const newBbox: [number, number, number, number] = [
          Math.round(newX0 * 10) / 10,
          Math.round(newY0 * 10) / 10,
          Math.round((newX0 + w) * 10) / 10,
          Math.round((newY0 + h) * 10) / 10,
        ];
        handleFieldChange(interaction.fieldId, {
          configuration: {
            ...(fields.find((f) => f.id === interaction.fieldId)?.configuration || {}),
            page: activePage,
            bbox: newBbox,
          },
        });
      } else if (interaction.type === "resize" && interaction.fieldId && interaction.initialBbox) {
        const [x0, y0, x1, y1] = interaction.initialBbox;
        let newX0 = x0;
        let newY0 = y0;
        let newX1 = x1;
        let newY1 = y1;

        if (interaction.handle === "se" || interaction.handle === "e") {
          newX1 = Math.max(x0 + 20, Math.min(curPageDims.width, x1 + deltaXPt));
        }
        if (interaction.handle === "se" || interaction.handle === "s") {
          newY1 = Math.max(y0 + 10, Math.min(curPageDims.height, y1 + deltaYPt));
        }
        if (interaction.handle === "nw") {
          newX0 = Math.max(0, Math.min(x1 - 20, x0 + deltaXPt));
          newY0 = Math.max(0, Math.min(y1 - 10, y0 + deltaYPt));
        }
        if (interaction.handle === "ne") {
          newX1 = Math.max(x0 + 20, Math.min(curPageDims.width, x1 + deltaXPt));
          newY0 = Math.max(0, Math.min(y1 - 10, y0 + deltaYPt));
        }
        if (interaction.handle === "sw") {
          newX0 = Math.max(0, Math.min(x1 - 20, x0 + deltaXPt));
          newY1 = Math.max(y0 + 10, Math.min(curPageDims.height, y1 + deltaYPt));
        }

        const newBbox: [number, number, number, number] = [
          Math.round(newX0 * 10) / 10,
          Math.round(newY0 * 10) / 10,
          Math.round(newX1 * 10) / 10,
          Math.round(newY1 * 10) / 10,
        ];
        handleFieldChange(interaction.fieldId, {
          configuration: {
            ...(fields.find((f) => f.id === interaction.fieldId)?.configuration || {}),
            page: activePage,
            bbox: newBbox,
          },
        });
      }
    };

    const handleWindowMouseUp = (e: MouseEvent) => {
      if (!pdfImgRef.current || !review) {
        setInteraction(null);
        return;
      }
      const rect = pdfImgRef.current.getBoundingClientRect();
      const curPageDims = review.pageDimensions?.find((p) => p.page === activePage) || {
        width: 595,
        height: 842,
      };
      const scaleX = curPageDims.width / rect.width;
      const scaleY = curPageDims.height / rect.height;

      if (interaction.type === "draw") {
        let dispX0 = Math.min(interaction.startClientX, e.clientX) - rect.left;
        let dispY0 = Math.min(interaction.startClientY, e.clientY) - rect.top;
        let dispX1 = Math.max(interaction.startClientX, e.clientX) - rect.left;
        let dispY1 = Math.max(interaction.startClientY, e.clientY) - rect.top;

        const widthPx = dispX1 - dispX0;
        const heightPx = dispY1 - dispY0;

        // If in explicit pick mode and just clicked (less than 15px drag), provide a comfortable standard box at click point
        if (pickingFieldForLocation && (widthPx < 15 || heightPx < 10)) {
          dispX1 = Math.min(rect.width - 10, dispX0 + Math.min(360, rect.width * 0.75));
          dispY1 = dispY0 + 26;
        }

        const effectiveW = dispX1 - dispX0;
        const effectiveH = dispY1 - dispY0;

        if (effectiveW > 12 && effectiveH > 8) {
          const ptX0 = Math.round(Math.max(0, dispX0 * scaleX) * 10) / 10;
          const ptY0 = Math.round(Math.max(0, dispY0 * scaleY) * 10) / 10;
          const ptX1 = Math.round(Math.min(curPageDims.width, dispX1 * scaleX) * 10) / 10;
          const ptY1 = Math.round(Math.min(curPageDims.height, dispY1 * scaleY) * 10) / 10;
          const chosenBbox: [number, number, number, number] = [ptX0, ptY0, ptX1, ptY1];

          if (pickingFieldForLocation === "new") {
            setNewFieldBbox(chosenBbox);
            setNewFieldPage(activePage);
            setPickingFieldForLocation(null);
            setShowAddField(true);
          } else if (pickingFieldForLocation) {
            const fId = pickingFieldForLocation;
            setPickingFieldForLocation(null);
            const targetF = fields.find((f) => f.id === fId);
            const newConfig = {
              ...(targetF?.configuration || {}),
              page: activePage,
              bbox: chosenBbox,
            };
            handleFieldChange(fId, { configuration: newConfig });
            setHighlightedFieldId(fId);
            if (targetF) {
              updateFormField(templateId, fId, {
                key: targetF.key,
                fieldType: targetF.fieldType,
                requiredness: targetF.requiredness,
                questionKey: targetF.questionKey || null,
                configuration: newConfig,
              }).catch((err) => console.error("Reposition save failed:", err));
            }
          } else {
            setNewFieldBbox(chosenBbox);
            setNewFieldPage(activePage);
            setShowAddField(true);
          }
        }
      } else if (
        (interaction.type === "move" || interaction.type === "resize") &&
        interaction.fieldId
      ) {
        const f = fields.find((f) => f.id === interaction.fieldId);
        if (f && f.configuration) {
          updateFormField(templateId, f.id, {
            key: f.key,
            fieldType: f.fieldType,
            requiredness: f.requiredness,
            questionKey: f.questionKey || null,
            configuration: f.configuration,
          }).catch((err) => {
            console.error("Failed to auto-save field coordinates:", err);
          });
        }
      }
      setInteraction(null);
    };

    window.addEventListener("mousemove", handleWindowMouseMove);
    window.addEventListener("mouseup", handleWindowMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleWindowMouseMove);
      window.removeEventListener("mouseup", handleWindowMouseUp);
    };
  }, [interaction, activePage, fields, review, templateId, pickingFieldForLocation]);

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!canEdit) return;
    setInteraction({
      type: "draw",
      startClientX: e.clientX,
      startClientY: e.clientY,
      currentClientX: e.clientX,
      currentClientY: e.clientY,
    });
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
                  Approve & Publish
                </button>
              )}

              {review.status === "published" && (
                <button
                  onClick={handleArchive}
                  disabled={saving || publishing}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-600 text-xs font-medium transition-colors cursor-pointer"
                >
                  <FolderArchive className="w-3.5 h-3.5" /> Archive
                </button>
              )}

              <button
                type="button"
                onClick={handleDeleteForm}
                disabled={saving || publishing}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-red-200 bg-red-50/40 hover:bg-red-50 text-red-600 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
                title="Permanently delete this official form"
              >
                <Trash2 className="w-3.5 h-3.5" /> Delete
              </button>
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

            {/* Middle: Canvas interaction hint */}
            <div className="hidden lg:flex items-center gap-2 text-xs text-slate-300 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Canvas Ready: Drag empty space to create • Drag boxes to move or resize</span>
            </div>

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

          {/* Explicit Pick Location Guidance Banner */}
          {pickingFieldForLocation && (
            <div className="px-4 py-2 bg-[#6551f3] text-white text-xs font-semibold flex items-center justify-between shrink-0 shadow-md">
              <span className="flex items-center gap-2">
                <Target className="w-4 h-4 animate-spin text-white" />
                {pickingFieldForLocation === "new"
                  ? "Click or drag directly on the PDF to choose the place for the new field."
                  : `Click or drag directly on the PDF to set the position for "${fields.find((f) => f.id === pickingFieldForLocation)?.translations?.[0]?.label || "field"}"`}
              </span>
              <button
                type="button"
                onClick={() => {
                  if (pickingFieldForLocation === "new") {
                    setShowAddField(true);
                  }
                  setPickingFieldForLocation(null);
                }}
                className="text-xs bg-indigo-700 hover:bg-indigo-800 text-white px-2.5 py-1 rounded underline font-medium"
              >
                Cancel
              </button>
            </div>
          )}

          {/* Canvas Viewport */}
          <div
            ref={pdfContainerRef}
            className="flex-1 overflow-auto p-4 flex items-start justify-center bg-slate-900 select-none"
          >
            <div
              className="relative bg-white rounded shadow-2xl transition-transform origin-top cursor-crosshair select-none"
              style={{
                transform: `scale(${zoomScale})`,
                width: "100%",
                maxWidth: "600px",
              }}
              onMouseDown={handleCanvasMouseDown}
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
                  const isCurrentlyMoving =
                    interaction?.type === "move" && interaction?.fieldId === field.id;
                  const primaryLabel = field.translations?.[0]?.label || field.key;

                  return (
                    <div
                      key={field.id}
                      onMouseDown={(e) => {
                        if (!canEdit) return;
                        e.stopPropagation();
                        setHighlightedFieldId(field.id);
                        document
                          .getElementById(`field-card-${field.id}`)
                          ?.scrollIntoView({ behavior: "smooth", block: "center" });

                        const initial = [...bbox] as [number, number, number, number];
                        setInteraction({
                          type: "move",
                          fieldId: field.id,
                          initialBbox: initial,
                          startClientX: e.clientX,
                          startClientY: e.clientY,
                          currentClientX: e.clientX,
                          currentClientY: e.clientY,
                        });
                      }}
                      style={{
                        top: `${topPct}%`,
                        left: `${leftPct}%`,
                        width: `${widthPct}%`,
                        height: `${heightPct}%`,
                      }}
                      className={`absolute rounded border-2 transition-colors flex items-start p-0.5 group select-none ${
                        isCurrentlyMoving
                          ? "border-[#6551f3] bg-[#6551f3]/35 shadow-lg z-30 cursor-grabbing"
                          : isHighlighted
                          ? "border-[#6551f3] bg-[#6551f3]/25 shadow-[0_0_0_3px_rgba(101,81,243,0.35)] z-20 cursor-grab"
                          : "border-indigo-500/80 bg-indigo-500/15 hover:border-indigo-600 hover:bg-indigo-500/25 z-10 cursor-grab"
                      }`}
                      title={`[${idx + 1}] ${primaryLabel} (Drag to move, use handles to resize)`}
                    >
                      <span
                        className={`text-[9px] font-mono font-bold px-1 rounded shadow-xs truncate max-w-[130px] leading-tight select-none pointer-events-none ${
                          isHighlighted
                            ? "bg-[#6551f3] text-white"
                            : "bg-indigo-900/80 text-white group-hover:bg-indigo-600"
                        }`}
                      >
                        [{idx + 1}] {primaryLabel}
                      </span>

                      {/* Delete button on highlighted box */}
                      {isHighlighted && canEdit && (
                        <button
                          type="button"
                          onMouseDown={(e) => e.stopPropagation()}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteField(field.id);
                          }}
                          className="absolute -top-3 -right-3 w-5 h-5 rounded-full bg-red-600 hover:bg-red-700 text-white flex items-center justify-center shadow-lg z-50 cursor-pointer transition-transform hover:scale-125"
                          title="Delete Field (or press Delete/Backspace)"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      )}

                      {/* Resize handles shown when field is highlighted */}
                      {isHighlighted && canEdit && (
                        <>
                          {/* Bottom-right handle */}
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              const initial = [...bbox] as [number, number, number, number];
                              setInteraction({
                                type: "resize",
                                fieldId: field.id,
                                handle: "se",
                                initialBbox: initial,
                                startClientX: e.clientX,
                                startClientY: e.clientY,
                                currentClientX: e.clientX,
                                currentClientY: e.clientY,
                              });
                            }}
                            className="absolute -bottom-1.5 -right-1.5 w-3 h-3 bg-white border-2 border-[#6551f3] rounded-xs cursor-se-resize shadow-md z-30 hover:scale-125 transition-transform"
                            title="Drag to resize width and height"
                          />
                          {/* Right edge handle */}
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              const initial = [...bbox] as [number, number, number, number];
                              setInteraction({
                                type: "resize",
                                fieldId: field.id,
                                handle: "e",
                                initialBbox: initial,
                                startClientX: e.clientX,
                                startClientY: e.clientY,
                                currentClientX: e.clientX,
                                currentClientY: e.clientY,
                              });
                            }}
                            className="absolute top-1/2 -right-1.5 -translate-y-1/2 w-2 h-4 bg-white border-2 border-[#6551f3] rounded-xs cursor-ew-resize shadow-md z-30 hover:scale-125 transition-transform"
                            title="Drag to adjust width"
                          />
                          {/* Bottom edge handle */}
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              const initial = [...bbox] as [number, number, number, number];
                              setInteraction({
                                type: "resize",
                                fieldId: field.id,
                                handle: "s",
                                initialBbox: initial,
                                startClientX: e.clientX,
                                startClientY: e.clientY,
                                currentClientX: e.clientX,
                                currentClientY: e.clientY,
                              });
                            }}
                            className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-4 h-2 bg-white border-2 border-[#6551f3] rounded-xs cursor-ns-resize shadow-md z-30 hover:scale-125 transition-transform"
                            title="Drag to adjust height"
                          />
                          {/* Top-left handle */}
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              const initial = [...bbox] as [number, number, number, number];
                              setInteraction({
                                type: "resize",
                                fieldId: field.id,
                                handle: "nw",
                                initialBbox: initial,
                                startClientX: e.clientX,
                                startClientY: e.clientY,
                                currentClientX: e.clientX,
                                currentClientY: e.clientY,
                              });
                            }}
                            className="absolute -top-1.5 -left-1.5 w-3 h-3 bg-white border-2 border-[#6551f3] rounded-xs cursor-nw-resize shadow-md z-30 hover:scale-125 transition-transform"
                            title="Drag to resize"
                          />
                          {/* Top-right handle */}
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              const initial = [...bbox] as [number, number, number, number];
                              setInteraction({
                                type: "resize",
                                fieldId: field.id,
                                handle: "ne",
                                initialBbox: initial,
                                startClientX: e.clientX,
                                startClientY: e.clientY,
                                currentClientX: e.clientX,
                                currentClientY: e.clientY,
                              });
                            }}
                            className="absolute -top-1.5 -right-1.5 w-3 h-3 bg-white border-2 border-[#6551f3] rounded-xs cursor-ne-resize shadow-md z-30 hover:scale-125 transition-transform"
                            title="Drag to resize"
                          />
                          {/* Bottom-left handle */}
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              const initial = [...bbox] as [number, number, number, number];
                              setInteraction({
                                type: "resize",
                                fieldId: field.id,
                                handle: "sw",
                                initialBbox: initial,
                                startClientX: e.clientX,
                                startClientY: e.clientY,
                                currentClientX: e.clientX,
                                currentClientY: e.clientY,
                              });
                            }}
                            className="absolute -bottom-1.5 -left-1.5 w-3 h-3 bg-white border-2 border-[#6551f3] rounded-xs cursor-sw-resize shadow-md z-30 hover:scale-125 transition-transform"
                            title="Drag to resize"
                          />
                        </>
                      )}
                    </div>
                  );
                })}

              {/* Active Drawing Dragging Box Indicator */}
              {interaction?.type === "draw" && pdfImgRef.current && (() => {
                const rect = pdfImgRef.current.getBoundingClientRect();
                const leftPx = Math.min(interaction.startClientX, interaction.currentClientX) - rect.left;
                const topPx = Math.min(interaction.startClientY, interaction.currentClientY) - rect.top;
                const widthPx = Math.abs(interaction.currentClientX - interaction.startClientX);
                const heightPx = Math.abs(interaction.currentClientY - interaction.startClientY);

                return (
                  <div
                    style={{
                      top: `${topPx}px`,
                      left: `${leftPx}px`,
                      width: `${widthPx}px`,
                      height: `${heightPx}px`,
                    }}
                    className="absolute border-2 border-dashed border-[#6551f3] bg-[#6551f3]/25 pointer-events-none z-30 flex items-center justify-center"
                  >
                    <span className="bg-[#6551f3] text-white text-[9px] font-mono font-bold px-1.5 py-0.5 rounded shadow">
                      New Input Box
                    </span>
                  </div>
                );
              })()}
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
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleAutoDetect}
                  disabled={autoDetecting}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
                  title="Scan PDF layout to auto-detect input boxes"
                >
                  {autoDetecting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                  )}
                  Auto-Detect Fields
                </button>
                {fields.length > 0 && (
                  <button
                    type="button"
                    onClick={handleClearAllFields}
                    disabled={saving}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-red-50 text-slate-500 hover:text-red-600 text-xs font-medium transition-colors cursor-pointer"
                    title="Delete all fields from schema"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Clear All
                  </button>
                )}
                <button
                  onClick={() => {
                    const curPageDims = review?.pageDimensions?.find((p) => p.page === activePage) || {
                      width: 595,
                      height: 842,
                    };
                    if (!newFieldBbox) {
                      setNewFieldBbox(computeDefaultBbox(fields, activePage, curPageDims));
                      setNewFieldPage(activePage);
                    }
                    setModalError(null);
                    setShowAddField(true);
                  }}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-semibold transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" /> Add Field
                </button>
              </div>
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
                      <div className="flex items-center justify-center gap-2.5">
                        <button
                          type="button"
                          onClick={() => {
                            const curPageDims = review?.pageDimensions?.find((p) => p.page === activePage) || {
                              width: 595,
                              height: 842,
                            };
                            if (!newFieldBbox) {
                              setNewFieldBbox(computeDefaultBbox(fields, activePage, curPageDims));
                              setNewFieldPage(activePage);
                            }
                            setModalError(null);
                            setShowAddField(true);
                          }}
                          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs cursor-pointer"
                        >
                          <Plus className="w-4 h-4" /> Add Field Manually
                        </button>
                        <button
                          type="button"
                          onClick={handleAutoDetect}
                          disabled={autoDetecting}
                          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold cursor-pointer disabled:opacity-50"
                        >
                          {autoDetecting ? (
                            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                          ) : (
                            <Sparkles className="w-4 h-4 text-blue-600" />
                          )}
                          Scan & Auto-Detect
                        </button>
                      </div>
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
              <div className="space-y-6">
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
                    placeholder="e.g. Please ensure all personal and address information matches your official passport or identification."
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                {/* Required Documents / Evidence Checklist */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-xs font-semibold text-slate-700">
                      Required Evidence / Documents Checklist
                    </label>
                    <span className="text-xs text-slate-400">
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
                        className="flex-1 px-3.5 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
                      />
                      <button
                        type="button"
                        onClick={handleAddDoc}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors cursor-pointer"
                      >
                        <Plus className="w-4 h-4" /> Add Item
                      </button>
                    </div>
                  )}

                  {requiredDocs.length === 0 ? (
                    <p className="text-xs text-slate-400 italic py-2">
                      No required evidence documents added yet.
                    </p>
                  ) : (
                    <div className="space-y-1.5">
                      {requiredDocs.map((doc, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700"
                        >
                          <span className="flex items-center gap-2">
                            <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-[10px] font-bold flex items-center justify-center shrink-0">
                              {idx + 1}
                            </span>
                            <span>{doc}</span>
                          </span>
                          {canEdit && (
                            <button
                              type="button"
                              onClick={() => handleRemoveDoc(idx)}
                              className="text-slate-400 hover:text-red-500 p-1 cursor-pointer transition-colors"
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
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Internal Verification & Audit Notes
                  </label>
                  <textarea
                    rows={2}
                    disabled={!canEdit}
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="e.g. Verified by Review Officer against official guidelines."
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
                onClick={() => {
                  setShowAddField(false);
                  setPickingFieldForLocation("new");
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-colors shrink-0 ml-2"
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
