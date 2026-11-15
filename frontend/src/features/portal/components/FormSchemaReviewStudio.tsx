"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  ArrowLeft,
  CheckCircle,
  FileText,
  Save,
  Plus,
  Trash2,
  ChevronDown,
  AlertCircle,
  Sparkles,
  ShieldCheck,
  Loader2,
  FolderArchive,
  Layers,
  Check,
  MoreVertical,
  Columns2,
  CheckSquare,
  Table2,
  X,
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
  listOrganizationCategories,
  getCurrentOrganization,
  translateFormFieldLabel,
  autoMapFormFields,
  applyAutoMapFormFields,
  combineFieldsIntoChoice,
  groupFieldsIntoTableRow,
  syncTableColumns,
} from "../services/portalClient";
import {
  FormReviewDetail,
  FormFieldItem,
  FormFieldTableConfig,
  OrganizationCategory,
  AutoMapResponse,
} from "../types";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import {
  ReviewStudioAddFieldModal,
  ReviewStudioCanvas,
  ReviewStudioFieldCard,
  ReviewStudioMetadataTab,
  ReviewStudioTableGroupCard,
  TableGroupRow,
} from "./review-studio";

interface FormSchemaReviewStudioProps {
  templateId: string;
  onBack: () => void;
  onPublished?: (updated: FormReviewDetail) => void;
  canEdit?: boolean;
}

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
  const [autoMapping, setAutoMapping] = useState(false);
  const [autoMapResults, setAutoMapResults] = useState<AutoMapResponse | null>(null);
  const [applyingAutoMap, setApplyingAutoMap] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form metadata states
  const [name, setName] = useState("");
  const [category, setCategory] = useState("general");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [availableCategories, setAvailableCategories] = useState<OrganizationCategory[]>([]);
  const [submissionMethod, setSubmissionMethod] = useState("print_and_sign");
  const [instructions, setInstructions] = useState("");
  const [requiredDocs, setRequiredDocs] = useState<string[]>([]);
  const [newDocInput, setNewDocInput] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [activeTab, setActiveTab] = useState<"fields" | "metadata">("fields");
  const [paneView, setPaneView] = useState<"split" | "canvas" | "fields">("split");

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

  // Dropdown menu states
  const [showTopMenu, setShowTopMenu] = useState(false);
  const [showToolsMenu, setShowToolsMenu] = useState(false);
  const topMenuRef = useRef<HTMLDivElement>(null);
  const toolsMenuRef = useRef<HTMLDivElement>(null);

  // Multilingual translations states
  const [supportedLanguages, setSupportedLanguages] = useState<string[]>([
    "de",
    "en",
    "ar",
    "fr",
    "tr",
    "uk",
    "es",
    "ru",
  ]);
  const [expandedTranslationsFieldId, setExpandedTranslationsFieldId] = useState<string | null>(null);
  const [activeTranslationLang, setActiveTranslationLang] = useState<string>("ar");
  const [translatingFieldId, setTranslatingFieldId] = useState<string | null>(null);

  // Table grouping & multi-field bundling states
  const [selectedFieldIds, setSelectedFieldIds] = useState<Set<string>>(new Set());
  const [activeTableRows, setActiveTableRows] = useState<Record<string, number>>({});
  const [activeTableRowFilter, setActiveTableRowFilter] = useState<{
    tableKey: string;
    rowIndex: number;
  } | null>(null);
  const [syncingTableKey, setSyncingTableKey] = useState<string | null>(null);
  const [selectionMode, setSelectionMode] = useState<"choice" | "table" | null>(null);
  const [combineLabel, setCombineLabel] = useState("");
  const [combineFieldType, setCombineFieldType] = useState<
    "single_choice" | "multiple_choice"
  >("single_choice");
  const [groupTableTitle, setGroupTableTitle] = useState("");
  const [groupRowIndex, setGroupRowIndex] = useState(1);
  const [selectionSubmitting, setSelectionSubmitting] = useState(false);

  // Close dropdowns on outside click
  useEffect(() => {
    if (!showTopMenu && !showToolsMenu) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (topMenuRef.current && !topMenuRef.current.contains(e.target as Node)) {
        setShowTopMenu(false);
      }
      if (toolsMenuRef.current && !toolsMenuRef.current.contains(e.target as Node)) {
        setShowToolsMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showTopMenu, showToolsMenu]);

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
      setCategoryId(data.category_id || null);
      setSubmissionMethod(data.submissionMethod || "print_and_sign");
      setInstructions(data.instructions || "");
      setRequiredDocs(data.requiredDocuments || []);
      setReviewNotes(data.reviewNotes || "");

      listOrganizationCategories(true)
        .then((cats) => setAvailableCategories(cats))
        .catch(() => {});

      getCurrentOrganization()
        .then((org) => {
          if (org?.supported_languages && org.supported_languages.length > 0) {
            setSupportedLanguages(org.supported_languages);
            const firstNonSource = org.supported_languages.find(
              (l) => l !== (data.sourceLanguage || "de")
            );
            if (firstNonSource) {
              setActiveTranslationLang(firstNonSource);
            }
          }
        })
        .catch(() => {});
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

  const handleRunAutoMap = async () => {
    try {
      setAutoMapping(true);
      setError(null);
      const result = await autoMapFormFields(templateId);
      setAutoMapResults(result);
      if (result.suggestions.length > 0) {
        setSuccessMessage(
          `Found saved-detail matches for ${result.suggestions.length} of ${result.total_fields} questions.`
        );
      } else {
        setSuccessMessage(
          "Checked all questions, but found no new automatic matches."
        );
      }
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to auto-match questions";
      setError(msg);
    } finally {
      setAutoMapping(false);
    }
  };

  const handleApplyAllAutoMaps = async () => {
    if (!autoMapResults || autoMapResults.suggestions.length === 0) return;
    try {
      setApplyingAutoMap(true);
      setError(null);
      const mappings = autoMapResults.suggestions
        .filter((s) => Boolean(s.suggested_question_key))
        .map((s) => ({
          field_id: s.field_id,
          question_key: s.suggested_question_key!,
        }));

      if (mappings.length === 0) return;

      await applyAutoMapFormFields(templateId, mappings);

      setFields((prev) =>
        prev.map((f) => {
          const match = mappings.find((m) => m.field_id === f.id);
          if (match) {
            return { ...f, questionKey: match.question_key };
          }
          return f;
        })
      );
      setSuccessMessage(
        `Matched ${mappings.length} questions to saved personal details.`
      );
      setAutoMapResults(null);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to apply auto-mapped keys";
      setError(msg);
    } finally {
      setApplyingAutoMap(false);
    }
  };

  const handleFieldChange = useCallback(
    (
      fieldId: string,
      updates: Partial<FormFieldItem> & { label?: string; helpText?: string }
    ) => {
      setFields((prev) =>
        prev.map((f) => {
          if (f.id !== fieldId) return f;
          const updated = { ...f, ...updates };
          if (updates.label !== undefined) {
            const srcLang = review?.sourceLanguage || "de";
            const trans = [...(updated.translations || [])];
            const srcIndex = trans.findIndex((t) => t.language === srcLang);
            if (srcIndex >= 0) {
              trans[srcIndex] = { ...trans[srcIndex], label: updates.label };
            } else if (trans.length > 0) {
              trans[0] = { ...trans[0], label: updates.label };
            } else {
              trans.push({ language: srcLang, label: updates.label });
            }
            updated.translations = trans;
          }
          return updated;
        })
      );
    },
    [review?.sourceLanguage]
  );

  const handleFieldTranslationChange = (
    fieldId: string,
    language: string,
    newLabel: string
  ) => {
    setFields((prev) =>
      prev.map((f) => {
        if (f.id !== fieldId) return f;
        const trans = [...(f.translations || [])];
        const existingIdx = trans.findIndex((t) => t.language === language);
        if (existingIdx >= 0) {
          trans[existingIdx] = { ...trans[existingIdx], label: newLabel };
        } else {
          trans.push({ language, label: newLabel });
        }
        return { ...f, translations: trans };
      })
    );
  };

  const handleAutoTranslateField = async (
    fieldId: string,
    targetLanguage?: string
  ) => {
    const field = fields.find((f) => f.id === fieldId);
    if (!field) return;

    const sourceLang = review?.sourceLanguage || "de";
    const sourceLabel =
      field.translations?.find((t) => t.language === sourceLang)?.label ||
      field.translations?.[0]?.label ||
      field.key;

    if (!sourceLabel || !sourceLabel.trim()) {
      setError("Please provide a source label before auto-translating.");
      return;
    }

    const targets = targetLanguage
      ? [targetLanguage]
      : supportedLanguages.filter((l) => l !== sourceLang);

    if (targets.length === 0) return;

    try {
      setTranslatingFieldId(fieldId);
      setError(null);
      const translatedMap = await translateFormFieldLabel(
        sourceLabel,
        sourceLang,
        targets
      );

      setFields((prev) =>
        prev.map((f) => {
          if (f.id !== fieldId) return f;
          const trans = [...(f.translations || [])];
          for (const [lang, transText] of Object.entries(translatedMap)) {
            const idx = trans.findIndex((t) => t.language === lang);
            if (idx >= 0) {
              trans[idx] = { ...trans[idx], label: transText };
            } else {
              trans.push({ language: lang, label: transText });
            }
          }
          return { ...f, translations: trans };
        })
      );
      setSuccessMessage(
        targetLanguage
          ? `Field translated to ${targetLanguage.toUpperCase()}.`
          : `Field translated to ${Object.keys(translatedMap).length} supported languages.`
      );
      setTimeout(() => setSuccessMessage(null), 3500);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Failed to auto-translate field.";
      setError(msg);
    } finally {
      setTranslatingFieldId(null);
    }
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
        category_id: categoryId,
        submissionMethod,
        instructions: instructions.trim(),
        requiredDocuments: requiredDocs,
        reviewNotes: reviewNotes.trim(),
      });

      // 2. Persist fields
      for (const field of fields) {
        const srcLang = review.sourceLanguage || "de";
        const primaryTrans =
          field.translations?.find((t) => t.language === srcLang) ||
          field.translations?.[0];
        const isChoice =
          field.fieldType === "single_choice" ||
          field.fieldType === "multiple_choice" ||
          field.fieldType === "choice";
        const normalizedOptions =
          isChoice || (field.options && field.options.length > 0)
            ? (field.options || []).map((opt, optIdx) => ({
                ...(opt.id ? { id: opt.id } : {}),
                value: opt.value,
                position: opt.position ?? optIdx + 1,
                translations:
                  opt.translations && opt.translations.length > 0
                    ? opt.translations
                    : [{ language: srcLang, label: opt.label || opt.value }],
              }))
            : undefined;
        await updateFormField(templateId, field.id, {
          key: field.key,
          label: primaryTrans?.label || field.key,
          translations: field.translations,
          fieldType: field.fieldType,
          requiredness: field.requiredness,
          questionKey: field.questionKey || null,
          ...(normalizedOptions !== undefined
            ? { options: normalizedOptions }
            : {}),
        });
      }

      // 3. Save order
      const orderedIds = fields.map((f) => f.id);
      await reorderFormFields(templateId, orderedIds);

      setReview(updatedReview);
      setSuccessMessage("Form draft saved successfully.");
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save form draft";
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
    if (!confirm("Are you sure you want to remove this question from the form?")) return;
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
  }, [interaction, activePage, fields, review, templateId, pickingFieldForLocation, handleFieldChange]);

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
      setSuccessMessage(`Question "${newFieldLabel.trim()}" added to form.`);
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
      setSuccessMessage("Form has been successfully approved and published to the Official Portal!");
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

  const handleToggleMultiSelect = useCallback((fieldId: string) => {
    setSelectedFieldIds((prev) => {
      const next = new Set(prev);
      if (next.has(fieldId)) {
        next.delete(fieldId);
      } else {
        next.add(fieldId);
      }
      return next;
    });
  }, []);

  const handleSelectTableRow = useCallback((tableKey: string, rowIndex: number) => {
    setActiveTableRows((prev) => ({ ...prev, [tableKey]: rowIndex }));
    setActiveTableRowFilter({ tableKey, rowIndex });
  }, []);

  const handleSyncTableColumns = async (
    tableKey: string,
    sourceRowIndex: number
  ) => {
    try {
      setSyncingTableKey(tableKey);
      setError(null);
      const updated = await syncTableColumns(
        templateId,
        tableKey,
        sourceRowIndex
      );
      setReview(updated);
      setFields(updated.fields || []);
      setSuccessMessage("Applied Row 1 settings to all rows in this table.");
      setTimeout(() => setSuccessMessage(null), 3500);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to sync table rows."
      );
    } finally {
      setSyncingTableKey(null);
    }
  };

  const handleConfirmCombineChoice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFieldIds.size < 2 || !combineLabel.trim()) return;
    try {
      setSelectionSubmitting(true);
      setError(null);
      const orderedIds = fields
        .filter((f) => selectedFieldIds.has(f.id))
        .map((f) => f.id);
      const updated = await combineFieldsIntoChoice(templateId, {
        fieldIds: orderedIds,
        label: combineLabel.trim(),
        fieldType: combineFieldType,
      });
      setReview(updated);
      setFields(updated.fields || []);
      setSelectedFieldIds(new Set());
      setSelectionMode(null);
      setCombineLabel("");
      setSuccessMessage("Combined selected boxes into one choice question.");
      setTimeout(() => setSuccessMessage(null), 3500);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not combine selected boxes."
      );
    } finally {
      setSelectionSubmitting(false);
    }
  };

  const handleConfirmGroupTableRow = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFieldIds.size < 2 || !groupTableTitle.trim()) return;
    try {
      setSelectionSubmitting(true);
      setError(null);
      const orderedIds = fields
        .filter((f) => selectedFieldIds.has(f.id))
        .map((f) => f.id);
      const updated = await groupFieldsIntoTableRow(templateId, {
        fieldIds: orderedIds,
        tableTitle: groupTableTitle.trim(),
        rowIndex: Math.max(1, groupRowIndex),
      });
      setReview(updated);
      setFields(updated.fields || []);
      setSelectedFieldIds(new Set());
      setSelectionMode(null);
      setGroupTableTitle("");
      setGroupRowIndex(1);
      setSuccessMessage("Grouped selected fields into table row.");
      setTimeout(() => setSuccessMessage(null), 3500);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not group fields into table row."
      );
    } finally {
      setSelectionSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4 bg-[#0A0E17]">
        <Loader2 className="w-8 h-8 text-emerald-400 animate-spin motion-reduce:animate-none" />
        <p className="text-sm font-medium text-slate-400">Loading form questions and PDF preview...</p>
      </div>
    );
  }

  if (!review) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center bg-[#0A0E17]">
        <AlertCircle className="w-12 h-12 text-rose-400 mb-3" />
        <h3 className="text-lg font-bold text-slate-100">Form Not Found</h3>
        <p className="text-sm text-slate-400 mb-4">{error || "Unable to load review detail."}</p>
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#121A2A] border border-white/10 hover:bg-[#192338] text-slate-200 text-sm font-medium transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Return to Catalog
        </button>
      </div>
    );
  }

  const pdfUrl = `/api/organizations/current/forms/${templateId}/source-pdf`;

  return (
    <div className="flex flex-col h-full w-full min-w-0 max-w-full overflow-hidden bg-[#0A0E17]">
      {/* Top Action Bar */}
      <header className="backdrop-blur-md bg-slate-900/90 border-b border-slate-800 px-4 sm:px-6 py-2.5 sm:py-3 flex items-center justify-between shrink-0 shadow-2xs gap-3 min-w-0 sticky top-0 z-30">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onBack}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shrink-0 cursor-pointer"
            title="Back to Catalog"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-sm sm:text-base font-bold text-white truncate max-w-[200px] sm:max-w-xs md:max-w-md">
                {name || review.name}
              </h1>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] sm:text-xs font-mono font-semibold uppercase tracking-wider shrink-0 ${
                  review.status === "published"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                    : review.status === "archived"
                    ? "bg-slate-800 text-slate-400 border border-slate-700"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                }`}
              >
                {review.status === "published" ? "Live" : "Review"}
              </span>
              <span className="text-[11px] text-slate-400 hidden sm:inline shrink-0">
                {fields.length} {fields.length === 1 ? "Question" : "Questions"}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:flex items-center gap-1.5 mt-0.5 truncate">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>Side-by-Side Form Editor</span>
            </p>
          </div>
        </div>

        {/* Center: View Switcher (Split, Canvas, Fields) */}
        <div className="flex items-center rounded-xl bg-slate-950 p-0.5 border border-slate-800 shrink-0">
          <button
            type="button"
            onClick={() => setPaneView("split")}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              paneView === "split"
                ? "bg-slate-800 text-emerald-400 shadow-2xs border border-slate-700"
                : "text-slate-400 hover:text-white"
            }`}
            title="Dual-Pane Split View"
          >
            <Columns2 className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Split</span>
          </button>
          <button
            type="button"
            onClick={() => setPaneView("canvas")}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              paneView === "canvas"
                ? "bg-slate-800 text-emerald-400 shadow-2xs border border-slate-700"
                : "text-slate-400 hover:text-white"
            }`}
            title="PDF Canvas Only"
          >
            <FileText className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Canvas</span>
          </button>
          <button
            type="button"
            onClick={() => setPaneView("fields")}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              paneView === "fields"
                ? "bg-slate-800 text-emerald-400 shadow-2xs border border-slate-700"
                : "text-slate-400 hover:text-white"
            }`}
            title="Questions Editor Only"
          >
            <Layers className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Fields</span>
          </button>
        </div>

        {/* Studio Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {successMessage && (
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-medium">
              <Check className="w-3.5 h-3.5" />
              <span>{successMessage}</span>
            </div>
          )}
          {error && (
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{error}</span>
            </div>
          )}

          {canEdit && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleSaveDraft}
                disabled={saving || publishing}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
                title="Save current changes as draft"
              >
                {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5 text-slate-400" />}
                <span>Save Draft</span>
              </button>

              {review.status !== "published" && (
                <button
                  type="button"
                  onClick={handlePublish}
                  disabled={saving || publishing}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold shadow-[0_0_15px_rgba(16,185,129,0.35)] transition-all disabled:opacity-50 cursor-pointer"
                >
                  {publishing ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <CheckCircle className="w-3.5 h-3.5" />
                  )}
                  <span>Approve & Publish</span>
                </button>
              )}

              {/* More Actions Dropdown */}
              <div ref={topMenuRef} className="relative">
                <button
                  type="button"
                  onClick={() => setShowTopMenu(!showTopMenu)}
                  aria-expanded={showTopMenu}
                  aria-haspopup="menu"
                  className="inline-flex items-center justify-center w-8 h-8 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer"
                  title="More options"
                >
                  <MoreVertical className="w-4 h-4" />
                </button>

                {showTopMenu && (
                  <div
                    role="menu"
                    className="absolute right-0 mt-1.5 w-44 rounded-xl border border-slate-800 bg-[#0F1522] py-1 shadow-xl ring-1 ring-black/40 z-50 animate-in fade-in zoom-in-95 duration-100 text-xs font-medium text-slate-200"
                  >
                    {review.status === "published" && (
                      <button
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          setShowTopMenu(false);
                          handleArchive();
                        }}
                        disabled={saving || publishing}
                        className="flex w-full items-center gap-2 px-3 py-2 text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer"
                      >
                        <FolderArchive className="w-3.5 h-3.5 text-slate-400" />
                        <span>Archive Form</span>
                      </button>
                    )}
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        setShowTopMenu(false);
                        handleDeleteForm();
                      }}
                      disabled={saving || publishing}
                      className="flex w-full items-center gap-2 px-3 py-2 text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5 text-red-400" />
                      <span>Delete Form</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Main Dual-Pane Studio Body */}
      <div className="flex-1 flex min-w-0 w-full overflow-hidden">
        {/* Left Pane: Interactive Visual PDF Canvas & Placement Studio */}
        <ReviewStudioCanvas
          paneView={paneView}
          templateId={templateId}
          activePage={activePage}
          setActivePage={setActivePage}
          pageCount={review.pageCount || 1}
          zoomScale={zoomScale}
          setZoomScale={setZoomScale}
          pdfUrl={pdfUrl}
          pdfContainerRef={pdfContainerRef}
          pdfImgRef={pdfImgRef}
          canEdit={canEdit}
          pickingFieldForLocation={pickingFieldForLocation}
          onCancelPickingLocation={() => {
            if (pickingFieldForLocation === "new") {
              setShowAddField(true);
            }
            setPickingFieldForLocation(null);
          }}
          fields={fields}
          highlightedFieldId={highlightedFieldId}
          selectedFieldIds={selectedFieldIds}
          onToggleMultiSelect={handleToggleMultiSelect}
          activeTableRowFilter={activeTableRowFilter}
          onSelectField={(id) => setHighlightedFieldId(id)}
          onDeleteField={handleDeleteField}
          pageDimensions={review.pageDimensions}
          interaction={interaction}
          onStartDraw={handleCanvasMouseDown}
          onStartMove={(e, fieldId, initialBbox) => {
            setInteraction({
              type: "move",
              fieldId,
              initialBbox,
              startClientX: e.clientX,
              startClientY: e.clientY,
              currentClientX: e.clientX,
              currentClientY: e.clientY,
            });
          }}
          onStartResize={(e, fieldId, handle, initialBbox) => {
            setInteraction({
              type: "resize",
              fieldId,
              handle,
              initialBbox,
              startClientX: e.clientX,
              startClientY: e.clientY,
              currentClientX: e.clientX,
              currentClientY: e.clientY,
            });
          }}
        />

        {/* Right Pane: Schema Fields Editor & Review */}
        <div
          className={`${
            paneView === "canvas"
              ? "hidden"
              : paneView === "fields"
              ? "w-full"
              : "w-1/2"
          } min-w-0 flex flex-col bg-[#0A0E17] border-l border-slate-800 overflow-hidden`}
        >
          {/* Sub Navigation */}
          <div className="px-4 py-2 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2 bg-slate-900/60 shrink-0 min-w-0">
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                onClick={() => setActiveTab("fields")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer ${
                  activeTab === "fields"
                    ? "bg-slate-800 text-emerald-400 shadow-2xs border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Fields ({fields.length})</span>
              </button>
              <button
                onClick={() => setActiveTab("metadata")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer ${
                  activeTab === "metadata"
                    ? "bg-slate-800 text-emerald-400 shadow-2xs border border-slate-700"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Details</span>
              </button>
            </div>

            {activeTab === "fields" && canEdit && (
              <div className="flex items-center gap-2 shrink-0">
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
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold shadow-xs transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Field</span>
                </button>

                  <button
                    type="button"
                    onClick={handleRunAutoMap}
                    disabled={autoMapping || fields.length === 0}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-emerald-500/30 bg-slate-800 hover:bg-slate-700 text-emerald-400 text-xs font-semibold shadow-xs transition-colors cursor-pointer disabled:opacity-50"
                    title="Automatically match questions to saved personal details"
                  >
                    {autoMapping ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5" />
                    )}
                    <span>Auto-Match Saved Details</span>
                  </button>

                {/* Schema Tools & Options Dropdown */}
                <div ref={toolsMenuRef} className="relative">
                  <button
                    type="button"
                    onClick={() => setShowToolsMenu(!showToolsMenu)}
                    aria-expanded={showToolsMenu}
                    aria-haspopup="menu"
                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors cursor-pointer"
                    title="Form tools & options"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-slate-400" />
                    <span>Tools</span>
                    <ChevronDown className={`w-3 h-3 text-slate-400 transition-transform ${showToolsMenu ? "rotate-180" : ""}`} />
                  </button>

                  {showToolsMenu && (
                    <div
                      role="menu"
                      className="absolute right-0 mt-1.5 w-48 rounded-xl border border-slate-800 bg-[#0F1522] py-1 shadow-xl ring-1 ring-black/40 z-50 animate-in fade-in zoom-in-95 duration-100 text-xs font-medium text-slate-200"
                    >
                      <button
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          setShowToolsMenu(false);
                          handleRunAutoMap();
                        }}
                        disabled={autoMapping || fields.length === 0}
                        className="flex w-full items-center gap-2 px-3 py-2 text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer disabled:opacity-50"
                      >
                        {autoMapping ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                        ) : (
                          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                        )}
                        <span>Auto-Match Saved Details</span>
                      </button>

                      <button
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          setShowToolsMenu(false);
                          handleAutoDetect();
                        }}
                        disabled={autoDetecting}
                        className="flex w-full items-center gap-2 px-3 py-2 text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer disabled:opacity-50"
                      >
                        {autoDetecting ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                        ) : (
                          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                        )}
                        <span>Auto-Detect Fields</span>
                      </button>

                      {fields.length > 0 && (
                        <>
                          <div className="my-1 border-t border-slate-800" />
                          <button
                            type="button"
                            role="menuitem"
                            onClick={() => {
                              setShowToolsMenu(false);
                              handleClearAllFields();
                            }}
                            disabled={saving}
                            className="flex w-full items-center gap-2 px-3 py-2 text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5 text-red-400" />
                            <span>Clear All Fields</span>
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Editor Content Area */}
          <div className="flex-1 overflow-y-auto p-6 bg-[#0A0E17]">
            {activeTab === "fields" ? (
              <div className="space-y-4">
                <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 text-xs flex items-start gap-2.5">
                  <Sparkles className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-white">PDF Fields & Saved Personal Details:</span>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      Check each question label and link it to a saved detail (like First Name or Date of Birth) so returning applicants can fill it in 1 click.
                    </p>
                  </div>
                </div>

                {autoMapResults && (
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-card">
                    <div className="flex items-start gap-2.5">
                      <Sparkles className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-white">
                          Auto-Match Ready: {autoMapResults.suggestions.length} of {autoMapResults.total_fields} questions matched
                        </span>
                        <p className="text-emerald-300 text-[11px] mt-0.5">
                          Review the suggestions below. Apply all matches at once, or accept them one by one.
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {autoMapResults.suggestions.length > 0 && (
                        <button
                          type="button"
                          onClick={handleApplyAllAutoMaps}
                          disabled={applyingAutoMap}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold shadow-xs transition-colors cursor-pointer disabled:opacity-50"
                        >
                          {applyingAutoMap ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Check className="w-3.5 h-3.5" />
                          )}
                          <span>Apply All ({autoMapResults.suggestions.length})</span>
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setAutoMapResults(null)}
                        className="px-2.5 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-xs font-medium transition-colors cursor-pointer"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                )}

                {fields.length === 0 ? (
                  <div className="text-center py-12 border-2 border-dashed border-slate-800 rounded-2xl bg-slate-900/40">
                    <FileText className="w-10 h-10 text-slate-600 mx-auto mb-2" />
                    <p className="text-sm font-semibold text-slate-300">No fields extracted</p>
                    <p className="text-xs text-slate-500 mt-1 mb-4">
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
                          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold shadow-xs cursor-pointer transition-all"
                        >
                          <Plus className="w-4 h-4" /> Add Field Manually
                        </button>
                        <button
                          type="button"
                          onClick={handleAutoDetect}
                          disabled={autoDetecting}
                          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold cursor-pointer disabled:opacity-50 transition-all"
                        >
                          {autoDetecting ? (
                            <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                          ) : (
                            <Sparkles className="w-4 h-4 text-emerald-400" />
                          )}
                          Scan & Auto-Detect
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  (() => {
                    const renderStudioFieldCard = (
                      field: FormFieldItem,
                      idx: number
                    ) => (
                      <ReviewStudioFieldCard
                        key={field.id}
                        field={field}
                        index={idx}
                        totalFields={fields.length}
                        canEdit={canEdit}
                        isHighlighted={highlightedFieldId === field.id}
                        isMultiSelected={selectedFieldIds.has(field.id)}
                        onToggleMultiSelect={
                          canEdit ? handleToggleMultiSelect : undefined
                        }
                        autoMapSuggestion={autoMapResults?.suggestions.find(
                          (s) => s.field_id === field.id
                        )}
                        sourceLanguage={review.sourceLanguage || "de"}
                        supportedLanguages={supportedLanguages}
                        expandedTranslationsFieldId={
                          expandedTranslationsFieldId
                        }
                        setExpandedTranslationsFieldId={
                          setExpandedTranslationsFieldId
                        }
                        activeTranslationLang={activeTranslationLang}
                        setActiveTranslationLang={setActiveTranslationLang}
                        translatingFieldId={translatingFieldId}
                        onSelectField={(fieldId, page) => {
                          setHighlightedFieldId(fieldId);
                          if (typeof page === "number") {
                            setActivePage(page);
                          }
                        }}
                        onFieldChange={handleFieldChange}
                        onFieldTranslationChange={handleFieldTranslationChange}
                        onAutoTranslateField={handleAutoTranslateField}
                        onMoveField={handleMoveField}
                        onDeleteField={handleDeleteField}
                      />
                    );

                    const renderedTableKeys = new Set<string>();
                    const elements: React.ReactNode[] = [];

                    fields.forEach((field, idx) => {
                      const tableCfg = field.configuration?.table as
                        | FormFieldTableConfig
                        | undefined;
                      if (tableCfg?.table_key) {
                        const tKey = String(tableCfg.table_key);
                        if (renderedTableKeys.has(tKey)) {
                          return;
                        }
                        renderedTableKeys.add(tKey);

                        const rowBuckets = new Map<
                          number,
                          {
                            rowLabel: string;
                            fields: Array<{
                              field: FormFieldItem;
                              globalIndex: number;
                            }>;
                          }
                        >();
                        fields.forEach((candidate, cIdx) => {
                          const cTbl = candidate.configuration?.table as
                            | FormFieldTableConfig
                            | undefined;
                          if (cTbl?.table_key !== tKey) return;
                          const rIdx = Number(cTbl.row_index || 1);
                          const bucket = rowBuckets.get(rIdx) || {
                            rowLabel:
                              cTbl.row_label ||
                              (rIdx === 1 ? "Applicant" : `Row ${rIdx}`),
                            fields: [],
                          };
                          bucket.fields.push({
                            field: candidate,
                            globalIndex: cIdx,
                          });
                          rowBuckets.set(rIdx, bucket);
                        });

                        const rows: TableGroupRow[] = Array.from(
                          rowBuckets.entries()
                        )
                          .sort(([a], [b]) => a - b)
                          .map(([rowIndex, bucket]) => ({
                            rowIndex,
                            rowLabel: bucket.rowLabel,
                            fields: bucket.fields.sort((a, b) => {
                              const ca = Number(
                                (
                                  a.field.configuration?.table as
                                    | FormFieldTableConfig
                                    | undefined
                                )?.col_index ?? a.globalIndex
                              );
                              const cb = Number(
                                (
                                  b.field.configuration?.table as
                                    | FormFieldTableConfig
                                    | undefined
                                )?.col_index ?? b.globalIndex
                              );
                              return ca - cb;
                            }),
                          }));

                        const activeRowIdx =
                          activeTableRows[tKey] ?? rows[0]?.rowIndex ?? 1;

                        elements.push(
                          <ReviewStudioTableGroupCard
                            key={`table-${tKey}`}
                            tableKey={tKey}
                            tableTitle={tableCfg.table_title || tKey}
                            tableDescription={tableCfg.table_description}
                            rows={rows}
                            activeRowIndex={activeRowIdx}
                            canEdit={canEdit}
                            syncing={syncingTableKey === tKey}
                            onSelectRow={handleSelectTableRow}
                            onSyncColumns={handleSyncTableColumns}
                            renderFieldCard={renderStudioFieldCard}
                          />
                        );
                        return;
                      }

                      elements.push(renderStudioFieldCard(field, idx));
                    });

                    return elements;
                  })()
                )}
              </div>
            ) : (
              /* General Metadata Tab */
              <ReviewStudioMetadataTab
                canEdit={canEdit}
                name={name}
                setName={setName}
                category={category}
                setCategory={setCategory}
                categoryId={categoryId}
                setCategoryId={setCategoryId}
                availableCategories={availableCategories}
                instructions={instructions}
                setInstructions={setInstructions}
                requiredDocs={requiredDocs}
                newDocInput={newDocInput}
                setNewDocInput={setNewDocInput}
                handleAddDoc={handleAddDoc}
                handleRemoveDoc={handleRemoveDoc}
                reviewNotes={reviewNotes}
                setReviewNotes={setReviewNotes}
              />
            )}
          </div>
        </div>
      </div>

      {/* Add Field Modal */}
      <ReviewStudioAddFieldModal
        showAddField={showAddField}
        onClose={() => {
          setShowAddField(false);
          setNewFieldBbox(null);
          setModalError(null);
        }}
        onSubmit={handleCreateField}
        addingField={addingField}
        modalError={modalError}
        newFieldLabel={newFieldLabel}
        setNewFieldLabel={setNewFieldLabel}
        newFieldKey={newFieldKey}
        setNewFieldKey={setNewFieldKey}
        newFieldType={newFieldType}
        setNewFieldType={setNewFieldType}
        newFieldRequired={newFieldRequired}
        setNewFieldRequired={setNewFieldRequired}
        newFieldQuestionKey={newFieldQuestionKey}
        setNewFieldQuestionKey={setNewFieldQuestionKey}
        newFieldBbox={newFieldBbox}
        newFieldPage={newFieldPage}
        onPickOnPdf={() => {
          setShowAddField(false);
          setPickingFieldForLocation("new");
        }}
      />

      {/* Multi-Select Action Bar & Modals */}
      {canEdit && selectedFieldIds.size >= 2 && (
        <div
          data-testid="studio-selection-bar"
          className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-md rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-3.5 shadow-2xl"
        >
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs font-bold text-[var(--text-primary)]">
              {selectedFieldIds.size} fields selected
            </span>
            <button
              type="button"
              onClick={() => {
                setSelectedFieldIds(new Set());
                setSelectionMode(null);
              }}
              className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          </div>

          {!selectionMode && (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  const firstSelected = fields.find((f) =>
                    selectedFieldIds.has(f.id)
                  );
                  setCombineLabel(
                    firstSelected?.translations?.[0]?.label || ""
                  );
                  setSelectionMode("choice");
                }}
                className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-3 py-1.5 text-xs font-bold cursor-pointer transition-colors"
              >
                <CheckSquare className="w-3.5 h-3.5" />
                <span>Combine into Choice Question</span>
              </button>
              <button
                type="button"
                onClick={() => setSelectionMode("table")}
                className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-muted)] hover:border-emerald-500/40 text-[var(--text-primary)] px-3 py-1.5 text-xs font-semibold cursor-pointer transition-colors"
              >
                <Table2 className="w-3.5 h-3.5 text-emerald-500" />
                <span>Group as Table Row</span>
              </button>
            </div>
          )}

          {selectionMode === "choice" && (
            <form
              onSubmit={handleConfirmCombineChoice}
              className="space-y-2.5 pt-1 border-t border-[var(--border-subtle)]"
            >
              <div>
                <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1">
                  Combined Question Label
                </label>
                <input
                  type="text"
                  required
                  value={combineLabel}
                  onChange={(e) => setCombineLabel(e.target.value)}
                  placeholder="e.g. Marital status or Gender"
                  className="input-field py-1.5 text-xs"
                />
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCombineFieldType("single_choice")}
                  className={`flex-1 rounded-lg border px-2.5 py-1.5 text-xs font-semibold cursor-pointer ${
                    combineFieldType === "single_choice"
                      ? "border-emerald-500 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                      : "border-[var(--border-subtle)] text-[var(--text-secondary)]"
                  }`}
                >
                  Pick one option
                </button>
                <button
                  type="button"
                  onClick={() => setCombineFieldType("multiple_choice")}
                  className={`flex-1 rounded-lg border px-2.5 py-1.5 text-xs font-semibold cursor-pointer ${
                    combineFieldType === "multiple_choice"
                      ? "border-emerald-500 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                      : "border-[var(--border-subtle)] text-[var(--text-secondary)]"
                  }`}
                >
                  Pick multiple
                </button>
              </div>
              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setSelectionMode(null)}
                  className="btn-secondary px-3 py-1.5 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={selectionSubmitting || !combineLabel.trim()}
                  className="btn-primary px-3 py-1.5 text-xs font-semibold"
                >
                  {selectionSubmitting ? "Combining..." : "Confirm Combine"}
                </button>
              </div>
            </form>
          )}

          {selectionMode === "table" && (
            <form
              onSubmit={handleConfirmGroupTableRow}
              className="space-y-2.5 pt-1 border-t border-[var(--border-subtle)]"
            >
              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-2">
                  <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1">
                    Table Title
                  </label>
                  <input
                    type="text"
                    required
                    value={groupTableTitle}
                    onChange={(e) => setGroupTableTitle(e.target.value)}
                    placeholder="e.g. Household members"
                    className="input-field py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-[var(--text-secondary)] mb-1">
                    Row #
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={50}
                    required
                    value={groupRowIndex}
                    onChange={(e) =>
                      setGroupRowIndex(Number(e.target.value) || 1)
                    }
                    className="input-field py-1.5 text-xs"
                  />
                </div>
              </div>
              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setSelectionMode(null)}
                  className="btn-secondary px-3 py-1.5 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={selectionSubmitting || !groupTableTitle.trim()}
                  className="btn-primary px-3 py-1.5 text-xs font-semibold"
                >
                  {selectionSubmitting ? "Grouping..." : "Save Row Group"}
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
