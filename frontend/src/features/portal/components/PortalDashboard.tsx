"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getCurrentOrganization,
  listOrganizationForms,
  deleteForm,
  listOrganizationCategories,
  updateFormCategory,
  autoCategorizeForms,
} from "../services/portalClient";
import {
  Organization,
  OrganizationFormSummary,
  OrganizationCategory,
} from "../types";
import { FormUploadModal } from "./FormUploadModal";
import { FormSchemaReviewStudio } from "./FormSchemaReviewStudio";
import { ShareFormModal } from "./ShareFormModal";
import { CategoryIcon } from "./CategoryIcon";
import {
  FileText,
  ShieldCheck,
  UploadCloud,
  Layers,
  Trash2,
  QrCode,
  MapPin,
  Globe,
  Mail,
  Phone,
  ExternalLink,
  Landmark,
  Info,
  Search,
  ChevronDown,
  Check,
  X,
  Sparkles,
  Tag,
  Folder,
} from "lucide-react";
import {
  resolveThemeConfig,
  getContrastTextColor,
} from "../utils/theme";

export function PortalDashboard() {
  const [org, setOrg] = useState<Organization | null>(null);
  const [forms, setForms] = useState<OrganizationFormSummary[]>([]);
  const [categories, setCategories] = useState<OrganizationCategory[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [activeCategoryMenuFormId, setActiveCategoryMenuFormId] = useState<string | null>(null);
  const [autoCategorizing, setAutoCategorizing] = useState(false);
  const [categoryToast, setCategoryToast] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingForms, setLoadingForms] = useState(false);

  // Forms filter & search state
  const [formSearchQuery, setFormSearchQuery] = useState("");
  const [formStatusFilter, setFormStatusFilter] = useState<string>("all");
  const [isUploadFormOpen, setIsUploadFormOpen] = useState(false);
  const [selectedTemplateIdForReview, setSelectedTemplateIdForReview] = useState<string | null>(null);
  const [sharingForm, setSharingForm] = useState<OrganizationFormSummary | null>(null);

  const fetchWorkspace = () => {
    setLoading(true);
    Promise.all([
      getCurrentOrganization(),
      listOrganizationForms().catch(() => []),
      listOrganizationCategories().catch(() => []),
    ])
      .then(([orgData, formsData, catsData]) => {
        setOrg(orgData);
        setForms(formsData);
        setCategories(catsData);
      })
      .catch((err) => {
        console.error("Workspace load error:", err);
      })
      .finally(() => setLoading(false));
  };

  const fetchCategories = () => {
    listOrganizationCategories()
      .then((data) => setCategories(data))
      .catch((err) => console.error("Categories load error:", err));
  };

  const fetchForms = () => {
    setLoadingForms(true);
    listOrganizationForms()
      .then((data) => setForms(data))
      .catch((err) => console.error("Forms load error:", err))
      .finally(() => setLoadingForms(false));
  };

  const handleDeleteForm = async (templateId: string, formName: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete "${formName}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await deleteForm(templateId);
      setForms((prev) => prev.filter((f) => f.id !== templateId));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete form");
    }
  };

  const handleQuickUpdateCategory = async (templateId: string, categoryId: string | null) => {
    try {
      const updatedForm = await updateFormCategory(templateId, categoryId);
      setForms((prev) =>
        prev.map((f) => (f.id === templateId ? { ...f, ...updatedForm } : f))
      );
      setActiveCategoryMenuFormId(null);
      fetchCategories();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update form category");
    }
  };

  const handleAutoCategorize = async () => {
    setAutoCategorizing(true);
    try {
      const res = await autoCategorizeForms();
      fetchForms();
      fetchCategories();
      setCategoryToast(
        res.categorized_count > 0
          ? `Successfully categorized ${res.categorized_count} official forms!`
          : "All forms are already categorized or matched."
      );
      setTimeout(() => setCategoryToast(null), 4000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to auto-categorize forms");
    } finally {
      setAutoCategorizing(false);
    }
  };

  useEffect(() => {
    fetchWorkspace();
  }, []);

  useEffect(() => {
    const handleDocumentClick = () => setActiveCategoryMenuFormId(null);
    document.addEventListener("click", handleDocumentClick);
    return () => document.removeEventListener("click", handleDocumentClick);
  }, []);

  const formsNeedingReviewCount = useMemo(() => {
    return forms.filter((f) => f.status === "needs_review").length;
  }, [forms]);

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { all: forms.length, uncategorized: 0 };
    categories.forEach((c) => {
      counts[c.id] = 0;
    });
    forms.forEach((f) => {
      const catId = f.categoryId || f.category_id;
      if (catId && counts[catId] !== undefined) {
        counts[catId]++;
      } else {
        counts.uncategorized++;
      }
    });
    return counts;
  }, [forms, categories]);

  const filteredForms = useMemo(() => {
    return forms.filter((f) => {
      if (formStatusFilter !== "all" && f.status !== formStatusFilter) {
        return false;
      }
      if (categoryFilter !== "all") {
        const formCatId = f.categoryId || f.category_id;
        if (categoryFilter === "uncategorized") {
          if (formCatId) return false;
        } else {
          if (formCatId !== categoryFilter) return false;
        }
      }
      if (formSearchQuery.trim().length > 0) {
        const q = formSearchQuery.toLowerCase();
        const matchesName = f.name.toLowerCase().includes(q);
        const matchesKey = f.key.toLowerCase().includes(q);
        const matchesCategory = (f.categoryName || f.category_name || f.category || "").toLowerCase().includes(q);
        return matchesName || matchesKey || matchesCategory;
      }
      return true;
    });
  }, [forms, formStatusFilter, categoryFilter, formSearchQuery]);

  // If Review Studio is open, take over the view
  if (selectedTemplateIdForReview) {
    return (
      <FormSchemaReviewStudio
        templateId={selectedTemplateIdForReview}
        onBack={() => {
          setSelectedTemplateIdForReview(null);
          fetchForms();
        }}
        onPublished={() => {
          fetchForms();
        }}
        canEdit={true}
      />
    );
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="h-8 w-64 bg-slate-200 rounded-lg animate-pulse mb-4" />
        <div className="h-4 w-96 bg-slate-100 rounded-md animate-pulse mb-8" />
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-slate-100 rounded-2xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const theme = resolveThemeConfig(org?.ui_theme_config);
  const isCompact = theme.layout_density === "compact";
  const primaryBtnStyle = {
    backgroundColor: theme.primary_color,
    color: getContrastTextColor(theme.primary_color),
  };

  const renderHeader = () => (
    <div>
      {/* Citizen / Authority Notice Banner if configured */}
      {theme.citizen_notice_banner && (
        <div className="mb-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-xs text-amber-900 flex items-center gap-3">
          <Info className="w-4 h-4 shrink-0 text-amber-600" />
          <span className="font-medium">{theme.citizen_notice_banner}</span>
        </div>
      )}

      {/* Workspace Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-slate-500 font-medium mb-4">
        <span className="hover:text-slate-700 cursor-pointer">Verwaltungsportal</span>
        <span className="text-slate-300">/</span>
        <span className="text-slate-600 font-medium">Behörden-Workspace</span>
        <span className="text-slate-300">/</span>
        <span className="text-indigo-600 font-semibold">Amtliche Formulare & Studio</span>
      </div>

      {/* Official Government Authority Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-5 pb-6 border-b border-slate-200">
        <div className="flex items-start gap-4">
          <div className="h-16 w-16 shrink-0 rounded-2xl border-2 border-slate-200 bg-white p-1.5 shadow-2xs flex items-center justify-center overflow-hidden">
            {org?.logo_storage_path ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={`/api/organizations/${org.id}/logo`}
                alt={`${org.name} logo`}
                className="h-full w-full object-contain"
              />
            ) : (
              <div className="w-full h-full rounded-xl bg-amber-50 flex items-center justify-center text-amber-700">
                <Landmark className="w-8 h-8 text-amber-600" />
              </div>
            )}
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                {org?.name || "Stadtverwaltung Stuttgart — Bürgeramt & Ausländerwesen"}
              </h1>
              {org?.is_verified_government ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  Verified Official Authority
                </span>
              ) : org?.verification_status === "pending_review" ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700">
                  Pending Verification
                </span>
              ) : null}
              <span className="rounded-full border border-indigo-100 bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700 capitalize">
                {org?.organization_type || "Government"}
              </span>
            </div>

            <p className="mt-1 text-xs text-slate-500 max-w-3xl leading-relaxed">
              {org?.description ||
                "Official municipal authority for citizen services, registration, civil status, and foreign affairs for the City of Stuttgart, Baden-Württemberg."}
            </p>

            {/* Official Authority Metadata Bar */}
            {theme.show_authority_metadata !== false && (
              <div className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-600">
                {org?.office_address && (
                  <span className="inline-flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{org.office_address}</span>
                  </span>
                )}
                {org?.official_website_url && (
                  <a
                    href={org.official_website_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 hover:underline"
                  >
                    <Globe className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                    <span>{org.official_website_url.replace(/^https?:\/\//, "")}</span>
                    <ExternalLink className="w-3 h-3 text-slate-400" />
                  </a>
                )}
                {org?.contact_email && (
                  <span className="inline-flex items-center gap-1">
                    <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <bdi>{org.contact_email}</bdi>
                  </span>
                )}
                {org?.contact_phone && (
                  <span className="inline-flex items-center gap-1">
                    <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <bdi>{org.contact_phone}</bdi>
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5 shrink-0 self-start lg:self-center">
          {org?.slug && theme.show_portal_link !== false && (
            <Link
              href={`/organizations/${org.slug}`}
              target="_blank"
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition-colors"
            >
              <Globe className="w-3.5 h-3.5 text-indigo-600" />
              <span>Public Portal</span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </Link>
          )}
          <button
            type="button"
            onClick={() => setIsUploadFormOpen(true)}
            style={primaryBtnStyle}
            className="inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold shadow-xs hover:opacity-90 active:scale-[0.98] transition-all cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload PDF</span>
          </button>
        </div>
      </div>
    </div>
  );

  const renderMetrics = () => {
    if (theme.show_metrics_strip === false) return null;
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Total forms</span>
            <span className="h-2 w-2 rounded-full bg-slate-300" />
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{forms.length}</div>
        </div>
        <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Live in portal</span>
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-emerald-600">
            {forms.filter((f) => f.status === "published").length}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Needs review</span>
            <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-amber-700">
            {formsNeedingReviewCount}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Archived</span>
            <span className="h-2 w-2 rounded-full bg-slate-300" />
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-slate-500">
            {forms.filter((f) => f.status === "archived").length}
          </div>
        </div>
      </div>
    );
  };

  const renderActions = () => (
    <div className="space-y-3">
      {/* Category Toast Alert */}
      {categoryToast && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-xs text-emerald-800 flex items-center justify-between shadow-2xs animate-in fade-in">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-semibold">{categoryToast}</span>
          </div>
          <button
            type="button"
            onClick={() => setCategoryToast(null)}
            className="text-emerald-500 hover:text-emerald-700 font-bold ml-2 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {/* Row 1: Status Filters + Search */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
          {[
            { id: "all", label: "All", count: forms.length },
            { id: "needs_review", label: "Needs Review", count: formsNeedingReviewCount },
            { id: "published", label: "Published", count: forms.filter((f) => f.status === "published").length },
            { id: "archived", label: "Archived", count: forms.filter((f) => f.status === "archived").length },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setFormStatusFilter(tab.id)}
              className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium transition-all cursor-pointer ${
                formStatusFilter === tab.id
                  ? "bg-slate-900 text-white shadow-2xs"
                  : "bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-50 border border-slate-200"
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[10px] font-mono rounded-full px-1.5 py-0.2 ${
                  formStatusFilter === tab.id
                    ? "bg-white/20 text-white"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-80">
          <div className="pointer-events-none absolute inset-y-0 start-0 flex items-center ps-3 text-slate-400">
            <Search className="w-3.5 h-3.5" />
          </div>
          <input
            type="text"
            value={formSearchQuery}
            onChange={(e) => setFormSearchQuery(e.target.value)}
            placeholder="Search forms..."
            className="w-full rounded-xl border border-slate-200 bg-white py-1.5 ps-8 pe-3 text-xs text-slate-900 placeholder-slate-400 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/15 transition-all"
          />
        </div>
      </div>

      {/* Row 2: Category Filter Pills + Auto-Categorize Button */}
      {(categories.length > 0 || categoryCounts.uncategorized > 0) && (
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100">
          <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto py-0.5">
            <span className="text-[11px] font-semibold text-slate-400 mr-1 flex items-center gap-1">
              <Folder className="w-3 h-3" /> Category:
            </span>
            <button
              type="button"
              onClick={() => setCategoryFilter("all")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-all cursor-pointer ${
                categoryFilter === "all"
                  ? "bg-indigo-600 text-white shadow-2xs font-semibold"
                  : "bg-white text-slate-600 hover:bg-slate-50 border border-slate-200"
              }`}
            >
              <span>All Categories</span>
              <span
                className={`text-[10px] font-mono px-1 rounded-full ${
                  categoryFilter === "all"
                    ? "bg-white/20 text-white"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {forms.length}
              </span>
            </button>

            {categories.map((cat) => {
              const count = categoryCounts[cat.id] || 0;
              const isSelected = categoryFilter === cat.id;
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setCategoryFilter(cat.id)}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-all cursor-pointer ${
                    isSelected
                      ? "bg-indigo-600 text-white shadow-2xs font-semibold"
                      : "bg-white text-slate-600 hover:bg-slate-50 border border-slate-200"
                  }`}
                >
                  <CategoryIcon icon={cat.icon} className="w-3.5 h-3.5 shrink-0" />
                  <span>{cat.name}</span>
                  <span
                    className={`text-[10px] font-mono px-1 rounded-full ${
                      isSelected
                        ? "bg-white/20 text-white"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}

            {categoryCounts.uncategorized > 0 && (
              <button
                type="button"
                onClick={() => setCategoryFilter("uncategorized")}
                className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-all cursor-pointer ${
                  categoryFilter === "uncategorized"
                    ? "bg-amber-600 text-white shadow-2xs font-semibold"
                    : "bg-white text-amber-700 hover:bg-amber-50 border border-amber-200"
                }`}
              >
                <Tag className="w-3 h-3 text-amber-500" />
                <span>Uncategorized</span>
                <span
                  className={`text-[10px] font-mono px-1 rounded-full ${
                    categoryFilter === "uncategorized"
                      ? "bg-white/20 text-white"
                      : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {categoryCounts.uncategorized}
                </span>
              </button>
            )}
          </div>

          {categoryCounts.uncategorized > 0 && (
            <button
              type="button"
              disabled={autoCategorizing}
              onClick={handleAutoCategorize}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border border-indigo-200 bg-indigo-50/70 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
              title="Automatically match official forms to categories based on German keywords"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              <span>
                {autoCategorizing ? "Matching..." : "Auto-Categorize Official Forms"}
              </span>
            </button>
          )}
        </div>
      )}
    </div>
  );

  const renderForms = () => (
    <div>
      {/* Forms List Grid */}
      {loadingForms ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 rounded-2xl bg-slate-100 animate-pulse" />
          ))}
        </div>
      ) : filteredForms.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-2xs">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
            <FileText className="w-6 h-6" />
          </div>
          <h3 className="mt-3 text-sm font-semibold text-slate-900">
            No official forms found
          </h3>
          <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
            Upload your municipality’s official blank PDF forms to auto-detect fields and create interactive multilingual workflows.
          </p>
          <div className="mt-5">
            <button
              type="button"
              onClick={() => setIsUploadFormOpen(true)}
              style={primaryBtnStyle}
              className="inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold shadow-xs hover:opacity-90 transition-colors cursor-pointer"
            >
              <UploadCloud className="w-4 h-4" /> Upload PDF
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredForms.map((f) => (
            <div
              key={f.id}
              className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-2xs hover:border-slate-300 hover:shadow-xs transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${
                      f.status === "published"
                        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                        : f.status === "archived"
                        ? "border-slate-200 bg-slate-100 text-slate-600"
                        : "border-amber-200 bg-amber-50 text-amber-800"
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      f.status === "published" ? "bg-emerald-500" : f.status === "archived" ? "bg-slate-400" : "bg-amber-500"
                    }`} />
                    <span>
                      {f.status === "published" ? "Live" : f.status === "needs_review" ? "Needs review" : "Archived"}
                    </span>
                  </span>
                  <span className="text-[11px] font-mono text-slate-400">
                    v{f.versionNumber}
                  </span>
                </div>

                <h3 className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600 line-clamp-1 transition-colors">
                  {f.name}
                </h3>
                <p className="text-[11px] font-mono text-slate-400 mt-0.5 truncate">{f.key}</p>

                <div className="mt-3 flex items-center justify-between gap-2 text-xs">
                  <span className="inline-flex items-center gap-1 text-[11px] text-slate-600 bg-slate-50 border border-slate-200/80 px-2 py-0.5 rounded-md">
                    <FileText className="w-3 h-3 text-slate-400" />
                    <span>{f.fieldsCount} {f.fieldsCount === 1 ? "field" : "fields"}</span>
                  </span>

                  {/* Interactive Category Badge & Quick Dropdown */}
                  <div className="relative">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveCategoryMenuFormId(
                          activeCategoryMenuFormId === f.id ? null : f.id
                        );
                      }}
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium border transition-colors cursor-pointer ${
                        f.categoryId || f.category_id
                          ? "bg-indigo-50/70 border-indigo-200/80 text-indigo-700 hover:bg-indigo-100"
                          : "bg-slate-50 border-dashed border-slate-300 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                      }`}
                      title="Click to assign or change category"
                    >
                      <CategoryIcon
                        icon={f.categoryIcon || f.category_icon}
                        className="w-3 h-3 text-indigo-600"
                      />
                      <span className="truncate max-w-[120px]">
                        {f.categoryName || f.category_name || (f.category && f.category !== "general" ? f.category : "+ Categorize")}
                      </span>
                      <ChevronDown className="w-2.5 h-2.5 text-slate-400" />
                    </button>

                    {/* Popover Dropdown Menu */}
                    {activeCategoryMenuFormId === f.id && (
                      <div
                        onClick={(e) => e.stopPropagation()}
                        className="absolute right-0 bottom-full mb-1 z-30 w-56 rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg"
                      >
                        <div className="px-2 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                          Assign Category
                        </div>
                        <div className="max-h-48 overflow-y-auto space-y-0.5">
                          {categories.map((cat) => {
                            const isSelected =
                              (f.categoryId || f.category_id) === cat.id;
                            return (
                              <button
                                key={cat.id}
                                type="button"
                                onClick={() => handleQuickUpdateCategory(f.id, cat.id)}
                                className={`w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-xs transition-colors cursor-pointer text-start ${
                                  isSelected
                                    ? "bg-indigo-50 text-indigo-700 font-semibold"
                                    : "text-slate-700 hover:bg-slate-50"
                                }`}
                              >
                                <span className="flex items-center gap-2 truncate">
                                  <CategoryIcon
                                    icon={cat.icon}
                                    className="w-3.5 h-3.5 shrink-0 text-slate-500"
                                  />
                                  <span className="truncate">{cat.name}</span>
                                </span>
                                {isSelected && (
                                  <Check className="w-3.5 h-3.5 shrink-0 text-indigo-600" />
                                )}
                              </button>
                            );
                          })}
                        </div>
                        <div className="mt-1 pt-1 border-t border-slate-100">
                          <button
                            type="button"
                            onClick={() => handleQuickUpdateCategory(f.id, null)}
                            className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-slate-500 hover:bg-slate-50 hover:text-slate-700 cursor-pointer"
                          >
                            <X className="w-3.5 h-3.5" />
                            <span>Remove Category</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                <span className="text-[11px] text-slate-400 truncate">
                  {new Date(f.updatedAt).toLocaleDateString()}
                </span>
                <div className="flex items-center gap-1.5 shrink-0">
                  {f.status === "published" && (
                    <button
                      type="button"
                      onClick={() => setSharingForm(f)}
                      className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg border border-slate-200 bg-white text-[11px] font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors cursor-pointer"
                      title="Share Form & Counter QR Code"
                    >
                      <QrCode className="w-3 h-3 text-slate-500" />
                      <span>Share</span>
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setSelectedTemplateIdForReview(f.id)}
                    className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg bg-indigo-50 border border-indigo-200/80 text-[11px] font-medium text-indigo-700 hover:bg-indigo-100 transition-colors cursor-pointer"
                    title="Review Schema & PDF Layout"
                  >
                    <Layers className="w-3 h-3 text-indigo-600" />
                    <span>Review</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteForm(f.id, f.name)}
                    className="h-7 w-7 inline-flex items-center justify-center rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
                    title="Delete Form"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div
      className={`mx-auto max-w-7xl px-4 ${
        isCompact ? "py-4 sm:px-4 space-y-4" : "py-8 sm:px-6 lg:px-8 space-y-6"
      }`}
    >
      {(theme.section_order || ["header", "metrics", "actions", "forms"]).map((sec) => {
        if (sec === "header") return <React.Fragment key="header">{renderHeader()}</React.Fragment>;
        if (sec === "metrics") return <React.Fragment key="metrics">{renderMetrics()}</React.Fragment>;
        if (sec === "actions") return <React.Fragment key="actions">{renderActions()}</React.Fragment>;
        if (sec === "forms") return <React.Fragment key="forms">{renderForms()}</React.Fragment>;
        return null;
      })}

      {/* Modals */}
      <FormUploadModal
        isOpen={isUploadFormOpen}
        onClose={() => setIsUploadFormOpen(false)}
        onFormUploaded={(reviewDetail) => {
          setIsUploadFormOpen(false);
          fetchForms();
          setSelectedTemplateIdForReview(reviewDetail.templateId);
        }}
      />

      {sharingForm && (
        <ShareFormModal
          isOpen={!!sharingForm}
          onClose={() => setSharingForm(null)}
          form={{
            id: sharingForm.id,
            key: sharingForm.key,
            name: sharingForm.name,
            status: sharingForm.status,
          }}
          orgSlug={org?.slug}
        />
      )}
    </div>
  );
}
