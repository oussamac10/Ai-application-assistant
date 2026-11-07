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
} from "../services/portalClient";
import {
  OrganizationCategory,
  CategoryTranslation,
  OrganizationFormSummary,
} from "../types";
import { CategoryIcon } from "./CategoryIcon";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";

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

export function OrganizationCategoryManager() {
  const [categories, setCategories] = useState<OrganizationCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

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
  const [activeLangTab, setActiveLangTab] = useState("en");

  // Assigned Forms Modal State (TYPO3 sys_category record relations)
  const [assignedFormsModalCat, setAssignedFormsModalCat] = useState<OrganizationCategory | null>(null);
  const [allOrgForms, setAllOrgForms] = useState<OrganizationFormSummary[]>([]);
  const [selectedFormIds, setSelectedFormIds] = useState<string[]>([]);
  const [loadingAssignedForms, setLoadingAssignedForms] = useState(false);
  const [savingAssignedForms, setSavingAssignedForms] = useState(false);
  const [formFilterQuery, setFormFilterQuery] = useState("");

  const guidanceLanguages = useMemo(() => UNIVERSAL_LANGUAGES.slice(0, 8), []);

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
  }, []);

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
    setActiveLangTab("en");
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
    setTranslations(cat.translations ? { ...cat.translations } : {});
    setActiveLangTab("en");
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

      const payload = {
        name: name.trim(),
        slug: slug.trim() || undefined,
        icon,
        description: description.trim() || null,
        parent_id: parentId && parentId !== "none" ? parentId : null,
        sort_order: sortOrder,
        is_active: isActive,
        translations,
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

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900">
              Form Categories & Taxonomy
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-xl">
            Structure your official forms into hierarchical categories. Each category supports verified multilingual translations across all citizen guidance languages.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={openCreateModal}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-xs font-semibold text-white shadow-xs transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Category</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 flex items-center justify-between text-xs text-red-800">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-500 font-bold ml-2">✕</button>
        </div>
      )}

      {successMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-2 text-xs text-emerald-800">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMsg}</span>
        </div>
      )}

      {loading ? (
        <div className="py-12 flex flex-col items-center justify-center space-y-3">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          <p className="text-xs text-slate-500">Loading categories & taxonomy...</p>
        </div>
      ) : categories.length === 0 ? (
        <div className="py-12 border-2 border-dashed border-slate-200 rounded-2xl text-center p-8 bg-slate-50/50">
          <FolderTree className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-800">No Categories Defined</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto mb-4">
            You haven&apos;t created any categories yet. Create categories to organize your official administrative forms.
          </p>
          <button
            type="button"
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition-colors shadow-xs cursor-pointer"
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
                className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xs hover:border-blue-200 hover:shadow-xs transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-2.5">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-slate-100 border border-slate-200 text-slate-700 flex items-center justify-center shrink-0">
                        <CategoryIcon name={cat.icon} className="w-5 h-5 text-indigo-600" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-bold text-slate-900">{cat.name}</h4>
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
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
                        className="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                        title="Edit Category"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(cat)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                        title="Delete Category"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {cat.description && (
                    <p className="text-xs text-slate-500 line-clamp-2 mt-1">
                      {cat.description}
                    </p>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => openAssignedFormsModal(cat)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold transition-colors cursor-pointer border border-indigo-200/80"
                      title="Manage assigned official administrative forms"
                    >
                      <FileText className="w-3.5 h-3.5 text-indigo-600" />
                      <span>{cat.forms_count} {cat.forms_count === 1 ? "Form" : "Forms"}</span>
                      <span className="text-[10px] text-indigo-500 font-normal">Manage</span>
                    </button>
                    <span className="text-slate-400">Order: {cat.sort_order}</span>
                  </div>

                  {/* Language Badges */}
                  <div className="flex items-center gap-1">
                    <Globe className="w-3 h-3 text-slate-400" />
                    <span className="font-semibold text-slate-500 text-[10px]">
                      {translatedCount} / {guidanceLanguages.length} Languages
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl max-h-[92vh] flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
                  <FolderTree className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    {editingCategory ? "Edit Category & Translations" : "Create Official Category"}
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Flexible hierarchical taxonomy for official forms
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSave} className="p-6 overflow-y-auto space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Category Name (Primary) *
                  </label>
                  <input
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
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-none text-slate-900"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Slug / URL Identifier
                  </label>
                  <input
                    type="text"
                    value={slug}
                    onChange={(e) => setSlug(e.target.value)}
                    placeholder="e.g. housing-residence"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-blue-500 outline-none text-slate-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Icon
                  </label>
                  <select
                    value={icon}
                    onChange={(e) => setIcon(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-none text-slate-900 bg-white"
                  >
                    {AVAILABLE_ICONS.map((ic) => (
                      <option key={ic.id} value={ic.id}>
                        {ic.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Parent Category (Hierarchy)
                  </label>
                  <select
                    value={parentId}
                    onChange={(e) => setParentId(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-none text-slate-900 bg-white"
                  >
                    <option value="">None (Top-Level Category)</option>
                    {categories
                      .filter((c) => !editingCategory || c.id !== editingCategory.id)
                      .map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Sort Order
                  </label>
                  <input
                    type="number"
                    value={sortOrder}
                    onChange={(e) => setSortOrder(parseInt(e.target.value) || 0)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-none text-slate-900"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Default Description
                </label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Short explanation for citizens and caseworkers..."
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-none text-slate-900"
                />
              </div>

              {/* Multilingual Guidance Translations (Supported Languages) */}
              <div className="pt-3 border-t border-slate-200">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5">
                    <Globe className="w-4 h-4 text-blue-600" />
                    <span className="text-xs font-bold text-slate-800">
                      Multilingual Citizen Translations
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400">
                    Shown when citizens select their guidance language
                  </span>
                </div>

                {/* Language Switcher Tabs */}
                <div className="flex flex-wrap gap-1 mb-3 bg-slate-100 p-1 rounded-xl">
                  {guidanceLanguages.map((lang) => {
                    const hasTranslation = Boolean(translations[lang.code]?.name);
                    return (
                      <button
                        key={lang.code}
                        type="button"
                        onClick={() => setActiveLangTab(lang.code)}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                          activeLangTab === lang.code
                            ? "bg-white text-blue-700 shadow-2xs"
                            : "text-slate-600 hover:text-slate-900"
                        }`}
                      >
                        <span className="uppercase text-[10px] font-mono">{lang.code}</span>
                        <span>{lang.nativeName}</span>
                        {hasTranslation && (
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* Active Language Translation Input */}
                <div className="space-y-3 bg-slate-50/70 p-3.5 rounded-xl border border-slate-200">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Translated Category Name ({activeLangTab.toUpperCase()})
                    </label>
                    <input
                      type="text"
                      value={translations[activeLangTab]?.name || ""}
                      onChange={(e) =>
                        handleTranslationChange(activeLangTab, "name", e.target.value)
                      }
                      placeholder={`e.g. Translated title in ${activeLangTab}...`}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 text-xs bg-white focus:ring-2 focus:ring-blue-500 outline-none text-slate-900"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                      Translated Description ({activeLangTab.toUpperCase()})
                    </label>
                    <textarea
                      rows={2}
                      value={translations[activeLangTab]?.description || ""}
                      onChange={(e) =>
                        handleTranslationChange(activeLangTab, "description", e.target.value)
                      }
                      placeholder={`Short explanation for citizens in ${activeLangTab}...`}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 text-xs bg-white focus:ring-2 focus:ring-blue-500 outline-none text-slate-900"
                    />
                  </div>
                </div>
              </div>

              {/* Modal Actions */}
              <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-xs font-semibold text-white shadow-xs transition-colors cursor-pointer"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 max-w-xl w-full p-6 space-y-4 max-h-[90vh] flex flex-col">
            <div className="flex items-start justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                  <CategoryIcon icon={assignedFormsModalCat.icon} className="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Assign Forms to &ldquo;{assignedFormsModalCat.name}&rdquo;
                  </h3>
                  <p className="text-xs text-slate-500">
                    Select official administrative forms that belong to this category.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setAssignedFormsModalCat(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                placeholder="Search official administrative forms..."
                value={formFilterQuery}
                onChange={(e) => setFormFilterQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 text-slate-900"
              />
            </div>

            <div className="overflow-y-auto flex-1 divide-y divide-slate-100 max-h-80 pr-1">
              {loadingAssignedForms ? (
                <div className="py-8 text-center">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-600 mx-auto mb-2" />
                  <span className="text-xs text-slate-500">Loading organization forms...</span>
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
                      className="flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-50 cursor-pointer transition-colors"
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
                          className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                        />
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-slate-900 truncate">
                            {form.name}
                          </p>
                          <p className="text-[11px] font-mono text-slate-400 truncate">
                            {form.key}
                          </p>
                        </div>
                      </div>
                      {otherCategory && !isChecked && (
                        <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-md truncate max-w-[120px]">
                          Currently: {otherCategory}
                        </span>
                      )}
                    </label>
                  );
                })
              )}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
              <span className="text-xs text-slate-500 font-medium">
                {selectedFormIds.length} forms selected
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setAssignedFormsModalCat(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 cursor-pointer transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={savingAssignedForms}
                  onClick={handleSaveAssignedForms}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs cursor-pointer transition-colors disabled:opacity-50"
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
