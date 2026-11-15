"use client";

import React, { useEffect, useState, useMemo } from "react";
import {
  Plus,
  Edit2,
  Trash2,
  FolderTree,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Layers,
  Globe,
  X,
  Loader2,
  FileText,
  Search,
} from "lucide-react";
import {
  listOrganizationCategories,
  createOrganizationCategory,
  updateOrganizationCategory,
  deleteOrganizationCategory,
  getCategoryForms,
  assignCategoryForms,
  listOrganizationForms,
  getCurrentOrganization,
} from "../services/portalClient";
import {
  OrganizationCategory,
  CategoryTranslation,
  OrganizationFormSummary,
} from "../types";
import { CategoryIcon } from "./CategoryIcon";
import { ModernSelect, ModernSelectOption } from "@/components/ui/ModernSelect";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import { LANGUAGE_MAP } from "./LanguageSelectionModal";

const AVAILABLE_ICONS = [
  { id: "Home", label: "Home / Housing" },
  { id: "Users", label: "Family / People" },
  { id: "Globe", label: "Immigration / Foreign" },
  { id: "Briefcase", label: "Work / Business" },
  { id: "Car", label: "Vehicles / Mobility" },
  { id: "HeartPulse", label: "Health / Social" },
  { id: "GraduationCap", label: "Education / Schools" },
  { id: "Building2", label: "Public Works / City" },
  { id: "Landmark", label: "Civic / Official" },
  { id: "ShieldCheck", label: "Security / Legal" },
  { id: "FileText", label: "Documents / Records" },
  { id: "Sparkles", label: "Special / Highlight" },
];

export interface OrganizationCategoryManagerProps {
  supportedLanguages?: string[];
}

export function OrganizationCategoryManager({
  supportedLanguages: propSupportedLanguages,
}: OrganizationCategoryManagerProps = {}) {
  const [categories, setCategories] = useState<OrganizationCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [fetchedSupportedLanguages, setFetchedSupportedLanguages] = useState<string[]>([]);

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<OrganizationCategory | null>(null);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [icon, setIcon] = useState("Home");
  const [description, setDescription] = useState("");
  const [parentId, setParentId] = useState<string>("");
  const [sortOrder, setSortOrder] = useState(0);
  const [isActive, setIsActive] = useState(true);
  const [translations, setTranslations] = useState<Record<string, CategoryTranslation>>({});
  const [selectedTranslationLang, setSelectedTranslationLang] = useState<string>("");

  // Assigned Forms Modal State (record relations)
  const [assignedFormsModalCat, setAssignedFormsModalCat] = useState<OrganizationCategory | null>(null);
  const [allOrgForms, setAllOrgForms] = useState<OrganizationFormSummary[]>([]);
  const [selectedFormIds, setSelectedFormIds] = useState<string[]>([]);
  const [loadingAssignedForms, setLoadingAssignedForms] = useState(false);
  const [savingAssignedForms, setSavingAssignedForms] = useState(false);
  const [formFilterQuery, setFormFilterQuery] = useState("");

  const effectiveLanguageCodes = useMemo(() => {
    if (propSupportedLanguages && propSupportedLanguages.length > 0) {
      return propSupportedLanguages;
    }
    if (fetchedSupportedLanguages.length > 0) {
      return fetchedSupportedLanguages;
    }
    return ["de", "en"];
  }, [propSupportedLanguages, fetchedSupportedLanguages]);

  const supportedLanguageOptions = useMemo(() => {
    return effectiveLanguageCodes.map((code) => {
      const fromMap = LANGUAGE_MAP.get(code);
      if (fromMap) {
        return {
          code,
          name: fromMap.name,
          nativeName: fromMap.native || fromMap.name,
        };
      }
      const fromUniversal = UNIVERSAL_LANGUAGES.find((l) => l.code === code);
      if (fromUniversal) {
        return {
          code,
          name: fromUniversal.englishName,
          nativeName: fromUniversal.nativeName || fromUniversal.englishName,
        };
      }
      return {
        code,
        name: code.toUpperCase(),
        nativeName: code.toUpperCase(),
      };
    });
  }, [effectiveLanguageCodes]);

  const activeLangOption = useMemo(() => {
    if (!selectedTranslationLang) return null;
    return (
      supportedLanguageOptions.find((l) => l.code === selectedTranslationLang) || {
        code: selectedTranslationLang,
        name: selectedTranslationLang.toUpperCase(),
        nativeName: selectedTranslationLang.toUpperCase(),
      }
    );
  }, [selectedTranslationLang, supportedLanguageOptions]);

  const configuredLanguageCodes = useMemo(() => {
    return Object.keys(translations);
  }, [translations]);

  const openAssignedFormsModal = async (cat: OrganizationCategory) => {
    setAssignedFormsModalCat(cat);
    setFormFilterQuery("");
    setLoadingAssignedForms(true);
    try {
      const [formsList, catFormIds] = await Promise.all([
        listOrganizationForms().catch(() => []),
        getCategoryForms(cat.id).catch(() => []),
      ]);
      setAllOrgForms(formsList);
      setSelectedFormIds(catFormIds);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load forms");
    } finally {
      setLoadingAssignedForms(false);
    }
  };

  const handleSaveAssignedForms = async () => {
    if (!assignedFormsModalCat) return;
    try {
      setSavingAssignedForms(true);
      await assignCategoryForms(assignedFormsModalCat.id, selectedFormIds);
      setSuccessMsg(`Updated form relations for "${assignedFormsModalCat.name}".`);
      setAssignedFormsModalCat(null);
      fetchCategories();
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save form relations");
    } finally {
      setSavingAssignedForms(false);
    }
  };

  const filteredOrgForms = useMemo(() => {
    if (!formFilterQuery.trim()) return allOrgForms;
    const q = formFilterQuery.toLowerCase();
    return allOrgForms.filter(
      (f) => f.name.toLowerCase().includes(q) || f.key.toLowerCase().includes(q)
    );
  }, [allOrgForms, formFilterQuery]);

  const fetchCategories = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listOrganizationCategories();
      setCategories(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load categories");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
    if (!propSupportedLanguages || propSupportedLanguages.length === 0) {
      getCurrentOrganization()
        .then((org) => {
          if (org?.supported_languages && org.supported_languages.length > 0) {
            setFetchedSupportedLanguages(org.supported_languages);
          }
        })
        .catch(() => {});
    }
  }, [propSupportedLanguages]);

  const openCreateModal = () => {
    setEditingCategory(null);
    setName("");
    setSlug("");
    setIcon("Home");
    setDescription("");
    setParentId("");
    setSortOrder((categories.length + 1) * 10);
    setIsActive(true);
    setTranslations({});
    setSelectedTranslationLang("");
    setModalOpen(true);
  };

  const openEditModal = (cat: OrganizationCategory) => {
    setEditingCategory(cat);
    setName(cat.name);
    setSlug(cat.slug);
    setIcon(cat.icon || "Home");
    setDescription(cat.description || "");
    setParentId(cat.parent_id || "");
    setSortOrder(cat.sort_order);
    setIsActive(cat.is_active);
    const existing = cat.translations ? { ...cat.translations } : {};
    setTranslations(existing);
    const existingCodes = Object.keys(existing);
    const firstMatch =
      existingCodes.find((c) => effectiveLanguageCodes.includes(c)) ||
      existingCodes[0] ||
      "";
    setSelectedTranslationLang(firstMatch);
    setModalOpen(true);
  };

  const handleDelete = async (cat: OrganizationCategory) => {
    if (!window.confirm(`Are you sure you want to delete category "${cat.name}"? Forms will be marked uncategorized.`)) {
      return;
    }
    try {
      setActionLoading(true);
      await deleteOrganizationCategory(cat.id);
      setCategories((prev) => prev.filter((c) => c.id !== cat.id));
      setSuccessMsg(`Category "${cat.name}" deleted.`);
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete category");
    } finally {
      setActionLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Category name is required.");
      return;
    }

    try {
      setActionLoading(true);
      setError(null);

      // Clean translations: only save entries that have a non-empty name
      const cleanedTranslations: Record<string, CategoryTranslation> = {};
      for (const [code, tr] of Object.entries(translations)) {
        if (tr && tr.name && tr.name.trim()) {
          cleanedTranslations[code] = {
            name: tr.name.trim(),
            description: tr.description?.trim() || null,
          };
        }
      }

      const payload = {
        name: name.trim(),
        slug: slug.trim() || undefined,
        icon,
        description: description.trim() || null,
        parent_id: parentId && parentId !== "none" ? parentId : null,
        sort_order: sortOrder,
        is_active: isActive,
        translations: cleanedTranslations,
      };

      if (editingCategory) {
        const updated = await updateOrganizationCategory(editingCategory.id, payload);
        setCategories((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
        setSuccessMsg(`Category "${updated.name}" updated.`);
      } else {
        const created = await createOrganizationCategory(payload);
        setCategories((prev) => [...prev, created]);
        setSuccessMsg(`Category "${created.name}" created.`);
      }

      setModalOpen(false);
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save category");
    } finally {
      setActionLoading(false);
    }
  };

  const handleTranslationChange = (lang: string, field: "name" | "description", val: string) => {
    setTranslations((prev) => ({
      ...prev,
      [lang]: {
        name: field === "name" ? val : prev[lang]?.name || "",
        description: field === "description" ? val : prev[lang]?.description || null,
      },
    }));
  };

  const handleSelectLanguage = (langCode: string) => {
    setSelectedTranslationLang(langCode);
    if (langCode && !translations[langCode]) {
      setTranslations((prev) => ({
        ...prev,
        [langCode]: { name: "", description: "" },
      }));
    }
  };

  const handleRemoveTranslation = (langCode: string) => {
    setTranslations((prev) => {
      const next = { ...prev };
      delete next[langCode];
      return next;
    });
    if (selectedTranslationLang === langCode) {
      const remaining = Object.keys(translations).filter((c) => c !== langCode);
      setSelectedTranslationLang(remaining[0] || "");
    }
  };

  const iconOptions: ModernSelectOption[] = useMemo(
    () =>
      AVAILABLE_ICONS.map((ic) => ({
        value: ic.id,
        label: ic.label,
        icon: <CategoryIcon icon={ic.id} className="w-4 h-4 text-emerald-400" />,
      })),
    []
  );

  const parentCategoryOptions: ModernSelectOption[] = useMemo(
    () => [
      {
        value: "",
        label: "None (Top-Level Category)",
        icon: <FolderTree className="w-4 h-4 text-slate-400" />,
      },
      ...categories
        .filter((c) => !editingCategory || c.id !== editingCategory.id)
        .map((c) => ({
          value: c.id,
          label: c.name,
          sublabel: c.description || undefined,
          icon: (
            <CategoryIcon
              icon={c.icon || "Layers"}
              className="w-4 h-4 text-emerald-400"
            />
          ),
        })),
    ],
    [categories, editingCategory]
  );

  const languageTranslateOptions: ModernSelectOption[] = useMemo(
    () => [
      {
        value: "",
        label: "-- Choose a supported language to translate --",
      },
      ...supportedLanguageOptions.map((lang) => {
        const isTranslated = Boolean(translations[lang.code]?.name?.trim());
        return {
          value: lang.code,
          label: `${lang.nativeName} (${lang.name})`,
          sublabel: lang.code.toUpperCase(),
          badge: (
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                isTranslated
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                  : "bg-[#151D2E] text-slate-400 border border-white/10"
              }`}
            >
              {lang.code.toUpperCase()}
              {isTranslated ? " ✓ Added" : ""}
            </span>
          ),
        };
      }),
    ],
    [supportedLanguageOptions, translations]
  );

  return (
    <div className="space-y-6 text-slate-100">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 border-b border-white/10">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-white">
              Form Categories & Taxonomy
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Structure your official forms into hierarchical categories. Each category supports verified multilingual translations across all citizen guidance languages.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={openCreateModal}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-xs font-bold text-slate-950 shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Category</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-between text-xs text-rose-200">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-300 font-bold ms-2 cursor-pointer">✕</button>
        </div>
      )}

      {successMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-2 text-xs text-emerald-300">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>{successMsg}</span>
        </div>
      )}

      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center space-y-3">
          <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
          <p className="text-xs text-slate-400">Loading categories & taxonomy...</p>
        </div>
      ) : categories.length === 0 ? (
        <div className="py-12 border-2 border-dashed border-white/10 rounded-2xl text-center p-8 bg-[#0A0E17]">
          <FolderTree className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-white">No Categories Defined</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto mb-4">
            You haven&apos;t created any categories yet. Create categories to organize your official administrative forms.
          </p>
          <button
            type="button"
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 text-slate-950 text-xs font-bold hover:bg-emerald-400 transition-colors shadow-xs cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Create Your First Category</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {categories.map((cat) => {
            const translatedCount = Object.keys(cat.translations || {}).length;
            const parentCat = cat.parent_id
              ? categories.find((c) => c.id === cat.parent_id)
              : null;

            return (
              <div
                key={cat.id}
                className="bg-[#0F1522] border border-white/10 rounded-2xl p-5 shadow-2xs hover:border-emerald-500/40 hover:shadow-xs transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-2.5">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-[#0A0E17] border border-white/10 text-slate-200 flex items-center justify-center shrink-0">
                        <CategoryIcon name={cat.icon} className="w-5 h-5 text-emerald-400" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-bold text-white">{cat.name}</h4>
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[#151D2E] text-slate-300 border border-white/10">
                            {cat.slug}
                          </span>
                        </div>
                        {parentCat && (
                          <p className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                            <Layers className="w-3 h-3" />
                            <span>Parent: {parentCat.name}</span>
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => openEditModal(cat)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors cursor-pointer"
                        title="Edit Category"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(cat)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                        title="Delete Category"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {cat.description && (
                    <p className="text-xs text-slate-400 line-clamp-2 mt-1">
                      {cat.description}
                    </p>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-white/[0.08] flex flex-wrap items-center justify-between gap-2 text-[11px]">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => openAssignedFormsModal(cat)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 font-semibold transition-colors cursor-pointer border border-emerald-500/30"
                      title="Manage assigned official administrative forms"
                    >
                      <FileText className="w-3.5 h-3.5 text-emerald-400" />
                      <span>{cat.forms_count} {cat.forms_count === 1 ? "Form" : "Forms"}</span>
                      <span className="text-[10px] text-emerald-300/80 font-normal">Manage</span>
                    </button>
                    <span className="text-slate-400">Order: {cat.sort_order}</span>
                  </div>

                  {/* Language Badges */}
                  <div className="flex items-center gap-1">
                    <Globe className="w-3 h-3 text-slate-500" />
                    <span className="font-semibold text-slate-400 text-[10px]">
                      {translatedCount} / {supportedLanguageOptions.length} Languages
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CREATE / EDIT CATEGORY MODAL */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#060910]/80 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-[#0F1522] rounded-2xl shadow-2xl border border-white/10 text-slate-100 w-full max-w-2xl max-h-[92vh] flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-[#0A0E17]/60">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
                  <FolderTree className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">
                    {editingCategory ? "Edit Category & Translations" : "Create Official Category"}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Flexible hierarchical taxonomy for official forms
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-[#151D2E] cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSave} className="p-6 overflow-y-auto space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="category-primary-name" className="block text-xs font-semibold text-slate-200 mb-1">
                    Category Name (Primary) *
                  </label>
                  <input
                    id="category-primary-name"
                    type="text"
                    required
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      if (!editingCategory && !slug) {
                        setSlug(
                          e.target.value
                            .toLowerCase()
                            .replace(/[^a-z0-9]+/g, "-")
                            .replace(/^-|-$/g, "")
                        );
                      }
                    }}
                    placeholder="e.g. Wohnen & Meldewesen"
                    className="w-full px-3 py-2 rounded-xl border border-white/10 bg-[#0A0E17] text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 outline-none"
                  />
                </div>

                <div>
                  <label htmlFor="category-slug" className="block text-xs font-semibold text-slate-200 mb-1">
                    Slug / URL Identifier
                  </label>
                  <input
                    id="category-slug"
                    type="text"
                    value={slug}
                    onChange={(e) => setSlug(e.target.value)}
                    placeholder="e.g. housing-residence"
                    className="w-full px-3 py-2 rounded-xl border border-white/10 bg-[#0A0E17] text-xs font-mono text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label htmlFor="category-icon-select" className="block text-xs font-semibold text-slate-200 mb-1">
                    Icon
                  </label>
                  <ModernSelect
                    id="category-icon-select"
                    value={icon}
                    onChange={(val) => setIcon(val)}
                    options={iconOptions}
                    placeholder="Select icon..."
                    searchable
                    searchPlaceholder="Search icons..."
                    aria-label="Icon"
                  />
                </div>

                <div>
                  <label htmlFor="category-parent-select" className="block text-xs font-semibold text-slate-200 mb-1">
                    Parent Category (Hierarchy)
                  </label>
                  <ModernSelect
                    id="category-parent-select"
                    value={parentId}
                    onChange={(val) => setParentId(val)}
                    options={parentCategoryOptions}
                    placeholder="None (Top-Level Category)"
                    searchable={parentCategoryOptions.length > 6}
                    searchPlaceholder="Search parent categories..."
                    aria-label="Parent Category (Hierarchy)"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-200 mb-1">
                    Sort Order
                  </label>
                  <input
                    type="number"
                    value={sortOrder}
                    onChange={(e) => setSortOrder(parseInt(e.target.value) || 0)}
                    className="w-full px-3 py-2 rounded-xl border border-white/10 bg-[#0A0E17] text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-200 mb-1">
                  Default Description
                </label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Short explanation for citizens and caseworkers..."
                  className="w-full px-3 py-2 rounded-xl border border-white/10 bg-[#0A0E17] text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 outline-none"
                />
              </div>

              {/* Multilingual Guidance Translations (Supported Languages) */}
              <div className="pt-3 border-t border-white/10">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 mb-2">
                  <div className="flex items-center gap-1.5">
                    <Globe className="w-4 h-4 text-emerald-400" />
                    <span className="text-xs font-bold text-white">
                      Multilingual Citizen Translations
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400">
                    Based on Supported Guidance Languages ({supportedLanguageOptions.length})
                  </span>
                </div>

                <p className="text-[11px] text-slate-400 mb-3">
                  Translate this category for citizens who select a different guidance language. Choose a language from your organization’s supported languages to add or edit its translation.
                </p>

                {/* Language Picker Dropdown */}
                <div className="mb-3">
                  <label htmlFor="translation-lang-select" className="block text-[11px] font-semibold text-slate-200 mb-1">
                    Choose Language to Translate
                  </label>
                  <ModernSelect
                    id="translation-lang-select"
                    value={selectedTranslationLang}
                    onChange={(val) => handleSelectLanguage(val)}
                    options={languageTranslateOptions}
                    placeholder="-- Choose a supported language to translate --"
                    searchable={languageTranslateOptions.length > 5}
                    searchPlaceholder="Search supported languages..."
                    aria-label="Choose Language to Translate"
                  />
                </div>

                {/* Configured Translation Badges / Selector (Only added languages!) */}
                {configuredLanguageCodes.length > 0 && (
                  <div className="mb-3">
                    <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                      Added Translations ({configuredLanguageCodes.length})
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {configuredLanguageCodes.map((code) => {
                        const opt = supportedLanguageOptions.find((l) => l.code === code);
                        const label = opt ? `${opt.nativeName} (${code.toUpperCase()})` : code.toUpperCase();
                        const isSelected = selectedTranslationLang === code;
                        const hasName = Boolean(translations[code]?.name?.trim());

                        return (
                          <div
                            key={code}
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all border ${
                              isSelected
                                ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40 shadow-2xs"
                                : "bg-[#0A0E17] text-slate-300 border-white/10 hover:bg-[#151D2E]"
                            }`}
                          >
                            <button
                              type="button"
                              onClick={() => setSelectedTranslationLang(code)}
                              className="flex items-center gap-1.5 cursor-pointer"
                            >
                              <span>{label}</span>
                              {hasName && (
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Translated" />
                              )}
                            </button>
                            <button
                              type="button"
                              onClick={() => handleRemoveTranslation(code)}
                              className="text-slate-400 hover:text-rose-400 p-0.5 rounded cursor-pointer transition-colors"
                              title="Remove translation"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Active Language Translation Input */}
                {selectedTranslationLang && activeLangOption ? (
                  <div className="space-y-3 bg-[#0A0E17] p-3.5 rounded-xl border border-white/10 animate-in fade-in duration-150">
                    <div className="flex items-center justify-between pb-2 border-b border-white/[0.08]">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded-md bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 font-mono text-[10px] font-bold uppercase">
                          {activeLangOption.code}
                        </span>
                        <span className="text-xs font-bold text-white">
                          {activeLangOption.nativeName}
                          {activeLangOption.name && activeLangOption.name !== activeLangOption.nativeName
                            ? ` (${activeLangOption.name})`
                            : ""}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveTranslation(selectedTranslationLang)}
                        aria-label={`Remove ${activeLangOption.code.toUpperCase()} translation`}
                        title="Remove active translation"
                        className="text-[11px] text-rose-400 hover:text-rose-300 font-medium inline-flex items-center gap-1 cursor-pointer"
                      >
                        <Trash2 className="w-3 h-3" />
                        <span>Remove</span>
                      </button>
                    </div>

                    <div>
                      <label htmlFor="translated-category-name" className="block text-[11px] font-semibold text-slate-200 mb-1">
                        Translated Category Name ({activeLangOption.code.toUpperCase()}) *
                      </label>
                      <input
                        id="translated-category-name"
                        type="text"
                        value={translations[selectedTranslationLang]?.name || ""}
                        onChange={(e) =>
                          handleTranslationChange(selectedTranslationLang, "name", e.target.value)
                        }
                        placeholder={`e.g. Translated title in ${activeLangOption.name}...`}
                        className="w-full px-3 py-2 rounded-lg border border-white/10 text-xs bg-[#0F1522] text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 outline-none"
                      />
                    </div>

                    <div>
                      <label htmlFor="translated-category-description" className="block text-[11px] font-semibold text-slate-200 mb-1">
                        Translated Description ({activeLangOption.code.toUpperCase()})
                      </label>
                      <textarea
                        id="translated-category-description"
                        rows={2}
                        value={translations[selectedTranslationLang]?.description || ""}
                        onChange={(e) =>
                          handleTranslationChange(selectedTranslationLang, "description", e.target.value)
                        }
                        placeholder={`Short explanation for citizens in ${activeLangOption.name}...`}
                        className="w-full px-3 py-2 rounded-lg border border-white/10 text-xs bg-[#0F1522] text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 outline-none"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="p-4 rounded-xl border border-dashed border-white/15 text-center bg-[#0A0E17]">
                    <Globe className="w-5 h-5 text-slate-500 mx-auto mb-1.5" />
                    <p className="text-xs font-semibold text-slate-200">No language selected</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Select a supported language from the dropdown above to add citizen guidance translations.
                    </p>
                  </div>
                )}
              </div>

              {/* Modal Actions */}
              <div className="pt-4 border-t border-white/10 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-[#151D2E] transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-xs font-bold text-slate-950 shadow-xs transition-colors cursor-pointer"
                >
                  {actionLoading ? "Saving..." : editingCategory ? "Update Category" : "Create Category"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MANAGE ASSIGNED FORMS MODAL (TYPO3 sys_category record relations) */}
      {assignedFormsModalCat && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#060910]/80 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-[#0F1522] rounded-3xl shadow-2xl border border-white/10 text-slate-100 max-w-xl w-full p-6 space-y-4 max-h-[90vh] flex flex-col">
            <div className="flex items-start justify-between pb-3 border-b border-white/[0.08]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0">
                  <CategoryIcon icon={assignedFormsModalCat.icon} className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    Assign Forms to &ldquo;{assignedFormsModalCat.name}&rdquo;
                  </h3>
                  <p className="text-xs text-slate-400">
                    Select official administrative forms that belong to this category.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setAssignedFormsModalCat(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-[#151D2E] cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute start-3 top-3 text-slate-500" />
              <input
                type="text"
                placeholder="Search official administrative forms..."
                value={formFilterQuery}
                onChange={(e) => setFormFilterQuery(e.target.value)}
                className="w-full ps-9 pe-3 py-2 text-xs rounded-xl border border-white/10 bg-[#0A0E17] text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
              />
            </div>

            <div className="overflow-y-auto flex-1 divide-y divide-white/[0.08] max-h-80 pe-1">
              {loadingAssignedForms ? (
                <div className="py-8 text-center">
                  <Loader2 className="w-6 h-6 animate-spin text-emerald-400 mx-auto mb-2" />
                  <span className="text-xs text-slate-400">Loading organization forms...</span>
                </div>
              ) : filteredOrgForms.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400">
                  No forms match your search query.
                </div>
              ) : (
                filteredOrgForms.map((form) => {
                  const isChecked = selectedFormIds.includes(form.id);
                  const otherCategory =
                    form.category_id && form.category_id !== assignedFormsModalCat.id
                      ? form.category_name || form.category
                      : null;
                  return (
                    <label
                      key={form.id}
                      className="flex items-center justify-between p-2.5 rounded-xl hover:bg-[#151D2E] cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedFormIds((prev) => [...prev, form.id]);
                            } else {
                              setSelectedFormIds((prev) => prev.filter((id) => id !== form.id));
                            }
                          }}
                          className="h-4 w-4 rounded border-white/20 bg-[#0A0E17] text-emerald-500 focus:ring-emerald-500/30 accent-emerald-500 cursor-pointer"
                        />
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-white truncate">
                            {form.name}
                          </p>
                          <p className="text-[11px] font-mono text-slate-400 truncate">
                            {form.key}
                          </p>
                        </div>
                      </div>
                      {otherCategory && !isChecked && (
                        <span className="text-[10px] text-slate-300 bg-[#151D2E] border border-white/10 px-2 py-0.5 rounded-md truncate max-w-[120px]">
                          Currently: {otherCategory}
                        </span>
                      )}
                    </label>
                  );
                })
              )}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-white/[0.08]">
              <span className="text-xs text-slate-400 font-medium">
                {selectedFormIds.length} forms selected
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setAssignedFormsModalCat(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-[#151D2E] cursor-pointer transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={savingAssignedForms}
                  onClick={handleSaveAssignedForms}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold shadow-xs cursor-pointer transition-colors disabled:opacity-50"
                >
                  {savingAssignedForms && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Save Relations</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
