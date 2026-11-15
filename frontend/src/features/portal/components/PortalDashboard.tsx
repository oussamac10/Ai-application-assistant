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
  provisionStarterTemplates,
  listCases,
  revokeCaseInvite,
  resendCaseInvite,
} from "../services/portalClient";
import {
  Case,
  Organization,
  OrganizationFormSummary,
  OrganizationCategory,
} from "../types";
import { FormUploadModal } from "./FormUploadModal";
import { FormSchemaReviewStudio } from "./FormSchemaReviewStudio";
import { ShareFormModal } from "./ShareFormModal";
import { NewCaseModal } from "./NewCaseModal";
import { InviteSuccessModal } from "./InviteSuccessModal";
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
  Loader2,
  UserPlus,
  Users,
  Ban,
  Send,
  KeyRound,
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
  const [isProvisioningStarters, setIsProvisioningStarters] = useState(false);
  const [categoryToast, setCategoryToast] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingForms, setLoadingForms] = useState(false);

  // Workspace tabs & Candidate Intakes state
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState<"forms" | "cases">("forms");
  const [cases, setCases] = useState<Case[]>([]);
  const [loadingCases, setLoadingCases] = useState(false);
  const [caseStatusFilter, setCaseStatusFilter] = useState<string>("all");
  const [caseSearchQuery, setCaseSearchQuery] = useState("");
  const [isNewCaseModalOpen, setIsNewCaseModalOpen] = useState(false);
  const [createdOrResentCase, setCreatedOrResentCase] = useState<Case | null>(null);
  const [caseActionLoadingId, setCaseActionLoadingId] = useState<string | null>(null);
  const [caseActionError, setCaseActionError] = useState<string | null>(null);

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
      typeof listCases === "function"
        ? Promise.resolve(listCases()).catch(() => [])
        : Promise.resolve([]),
    ])
      .then(([orgData, formsData, catsData, casesData]) => {
        setOrg(orgData);
        setForms(formsData);
        setCategories(catsData);
        setCases(Array.isArray(casesData) ? casesData : []);
      })
      .catch((err) => {
        console.error("Workspace load error:", err);
      })
      .finally(() => setLoading(false));
  };

  const fetchCases = () => {
    if (typeof listCases !== "function") return;
    setLoadingCases(true);
    Promise.resolve(listCases())
      .then((data) => setCases(Array.isArray(data) ? data : []))
      .catch((err) => console.error("Cases load error:", err))
      .finally(() => setLoadingCases(false));
  };

  const handleRevokeCase = async (publicId: string) => {
    setCaseActionLoadingId(publicId);
    setCaseActionError(null);
    try {
      const updated = await revokeCaseInvite(publicId);
      setCases((prev) =>
        prev.map((c) => (c.public_id === publicId ? updated : c))
      );
    } catch (err: unknown) {
      setCaseActionError(
        err instanceof Error ? err.message : "Failed to revoke invite link."
      );
    } finally {
      setCaseActionLoadingId(null);
    }
  };

  const handleResendCase = async (publicId: string) => {
    setCaseActionLoadingId(publicId);
    setCaseActionError(null);
    try {
      const updated = await resendCaseInvite(publicId);
      setCases((prev) =>
        prev.map((c) => (c.public_id === publicId ? updated : c))
      );
      setCreatedOrResentCase(updated);
    } catch (err: unknown) {
      setCaseActionError(
        err instanceof Error ? err.message : "Failed to resend candidate invite."
      );
    } finally {
      setCaseActionLoadingId(null);
    }
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

  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      if (caseStatusFilter !== "all" && c.status !== caseStatusFilter) {
        return false;
      }
      if (caseSearchQuery.trim().length > 0) {
        const q = caseSearchQuery.toLowerCase();
        const matchesName = c.candidate_name.toLowerCase().includes(q);
        const matchesEmail = c.candidate_email.toLowerCase().includes(q);
        const matchesForm = (c.form_title || "").toLowerCase().includes(q);
        return matchesName || matchesEmail || matchesForm;
      }
      return true;
    });
  }, [cases, caseStatusFilter, caseSearchQuery]);

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
        <div className="h-8 w-64 bg-slate-800 rounded-lg animate-pulse mb-4" />
        <div className="h-4 w-96 bg-slate-800/60 rounded-md animate-pulse mb-8" />
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-slate-800/50 border border-slate-800 rounded-2xl animate-pulse" />
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
    <div className="rounded-2xl border border-slate-800 bg-[#0F1522] p-6 sm:p-7 shadow-card relative overflow-hidden">
      {/* Background radial highlight */}
      <div className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-48 bg-emerald-500/5 blur-3xl rounded-full" />

      {/* Citizen / Authority Notice Banner if configured */}
      {theme.citizen_notice_banner && (
        <div className="mb-5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-200 flex items-center gap-3">
          <Info className="w-4 h-4 shrink-0 text-amber-400" />
          <span className="font-medium">{theme.citizen_notice_banner}</span>
        </div>
      )}

      {/* Workspace Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-slate-400 font-medium mb-4">
        <span className="hover:text-slate-200 cursor-pointer">Agency Portal</span>
        <span className="text-slate-600">/</span>
        <span className="text-slate-300 font-medium">Workspace</span>
        <span className="text-slate-600">/</span>
        <span className="text-emerald-400 font-semibold font-mono">
          {activeWorkspaceTab === "forms"
            ? "Official Forms & Studio"
            : "Candidate Intakes & Invites"}
        </span>
      </div>

      {/* Official Government Authority Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-5 pb-6 border-b border-slate-800">
        <div className="flex items-start gap-4">
          <div className="h-16 w-16 shrink-0 rounded-2xl border border-slate-800 bg-[#0A0E17] p-1.5 shadow-2xs flex items-center justify-center overflow-hidden">
            {org?.logo_storage_path ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={`/api/organizations/${org.id}/logo`}
                alt={`${org.name} logo`}
                className="h-full w-full object-contain"
              />
            ) : (
              <div className="w-full h-full rounded-xl bg-slate-900 flex items-center justify-center text-emerald-400">
                <Landmark className="w-8 h-8 text-emerald-400" />
              </div>
            )}
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
                {org?.name || "Organization Workspace"}
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-mono font-medium text-emerald-400">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 motion-reduce:hidden" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                LIVE WORKSPACE
              </span>
              {org?.is_verified_government ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  Verified Official Authority
                </span>
              ) : org?.verification_status === "pending_review" ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-400">
                  Pending Verification
                </span>
              ) : null}
              <span className="rounded-full border border-slate-700 bg-slate-800/60 px-2.5 py-0.5 text-xs font-mono text-slate-300 capitalize">
                {org?.organization_type || "Government"}
              </span>
            </div>

            <p className="mt-1.5 text-xs text-slate-400 max-w-3xl leading-relaxed">
              {org?.description ||
                "Official authority workspace for cross-border candidate intake, multilingual form mapping, and verified PDF processing."}
            </p>

            {/* Official Authority Metadata Bar */}
            {theme.show_authority_metadata !== false && (
              <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-400">
                {org?.office_address && (
                  <span className="inline-flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    <span>{org.office_address}</span>
                  </span>
                )}
                {org?.official_website_url && (
                  <a
                    href={org.official_website_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300 hover:underline"
                  >
                    <Globe className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>{org.official_website_url.replace(/^https?:\/\//, "")}</span>
                    <ExternalLink className="w-3 h-3 text-slate-500" />
                  </a>
                )}
                {org?.contact_email && (
                  <span className="inline-flex items-center gap-1">
                    <Mail className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    <bdi>{org.contact_email}</bdi>
                  </span>
                )}
                {org?.contact_phone && (
                  <span className="inline-flex items-center gap-1">
                    <Phone className="w-3.5 h-3.5 text-slate-500 shrink-0" />
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
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 shadow-2xs hover:bg-slate-800 hover:border-slate-600 transition-colors"
            >
              <Globe className="w-3.5 h-3.5 text-emerald-400" />
              <span>Public Portal</span>
              <ExternalLink className="w-3 h-3 text-slate-500" />
            </Link>
          )}
          <button
            type="button"
            data-testid="new-intake-header-btn"
            onClick={() => setIsNewCaseModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3.5 py-2 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/20 transition-colors cursor-pointer"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>New Intake</span>
          </button>
          <button
            type="button"
            onClick={() => setIsUploadFormOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-[0_0_20px_-3px_rgba(16,185,129,0.35)] active:scale-[0.98] transition-all cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload PDF</span>
          </button>
        </div>
      </div>

      {/* Workspace View Switcher */}
      <div className="pt-4 mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          data-testid="portal-tab-forms"
          onClick={() => setActiveWorkspaceTab("forms")}
          className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold transition-all cursor-pointer ${
            activeWorkspaceTab === "forms"
              ? "bg-emerald-500 text-slate-950 font-bold shadow-[0_0_12px_rgba(16,185,129,0.25)]"
              : "border border-slate-800 bg-[#0A0E17] text-slate-300 hover:bg-slate-800 hover:text-white"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Official Forms &amp; Studio</span>
          <span
            className={`rounded-full px-1.5 py-0.5 text-[10px] font-mono ${
              activeWorkspaceTab === "forms"
                ? "bg-slate-950/20 text-slate-950 font-bold"
                : "bg-slate-800 text-slate-400"
            }`}
          >
            {forms.length}
          </span>
        </button>

        <button
          type="button"
          data-testid="portal-tab-cases"
          onClick={() => setActiveWorkspaceTab("cases")}
          className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold transition-all cursor-pointer ${
            activeWorkspaceTab === "cases"
              ? "bg-emerald-500 text-slate-950 font-bold shadow-[0_0_12px_rgba(16,185,129,0.25)]"
              : "border border-slate-800 bg-[#0A0E17] text-slate-300 hover:bg-slate-800 hover:text-white"
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Candidate Intakes &amp; Invites</span>
          <span
            className={`rounded-full px-1.5 py-0.5 text-[10px] font-mono ${
              activeWorkspaceTab === "cases"
                ? "bg-slate-950/20 text-slate-950 font-bold"
                : "bg-slate-800 text-slate-400"
            }`}
          >
            {cases.length}
          </span>
        </button>
      </div>
    </div>
  );

  const renderMetrics = () => {
    if (theme.show_metrics_strip === false) return null;
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-800 border-t-2 border-t-emerald-500/60 bg-[#0F1522] p-4 sm:p-5 shadow-card transition-all hover:border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total forms</span>
            <span className="h-2 w-2 rounded-full bg-slate-600" />
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-mono">{forms.length}</div>
          <div className="mt-1 text-[11px] font-mono text-slate-500">ACTIVE SCHEMAS</div>
        </div>
        <div className="rounded-2xl border border-slate-800 border-t-2 border-t-emerald-500 bg-[#0F1522] p-4 sm:p-5 shadow-card transition-all hover:border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Live in portal</span>
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 motion-reduce:hidden" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-emerald-400 font-mono">
            {forms.filter((f) => f.status === "published").length}
          </div>
          <div className="mt-1 text-[11px] font-mono text-emerald-400/80">CITIZEN READY</div>
        </div>
        <div className="rounded-2xl border border-slate-800 border-t-2 border-t-amber-500 bg-[#0F1522] p-4 sm:p-5 shadow-card transition-all hover:border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Needs review</span>
            <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse motion-reduce:animate-none" />
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-amber-400 font-mono">
            {formsNeedingReviewCount}
          </div>
          <div className="mt-1 text-[11px] font-mono text-amber-400/80">ACTION REQUIRED</div>
        </div>
        <div className="rounded-2xl border border-slate-800 border-t-2 border-t-slate-700 bg-[#0F1522] p-4 sm:p-5 shadow-card transition-all hover:border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Archived</span>
            <span className="h-2 w-2 rounded-full bg-slate-700" />
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-400 font-mono">
            {forms.filter((f) => f.status === "archived").length}
          </div>
          <div className="mt-1 text-[11px] font-mono text-slate-500">OFFLINE</div>
        </div>
      </div>
    );
  };

  const renderActions = () => (
    <div className="space-y-3">
      {/* Category Toast Alert */}
      {categoryToast && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-xs text-emerald-300 flex items-center justify-between shadow-card animate-in fade-in">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="font-semibold">{categoryToast}</span>
          </div>
          <button
            type="button"
            onClick={() => setCategoryToast(null)}
            className="text-emerald-400 hover:text-emerald-300 font-bold ml-2 cursor-pointer"
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
                  ? "bg-emerald-500 text-slate-950 font-bold shadow-[0_0_12px_rgba(16,185,129,0.3)]"
                  : "bg-[#0F1522] text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800"
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[10px] font-mono rounded-full px-1.5 py-0.2 ${
                  formStatusFilter === tab.id
                    ? "bg-slate-950/30 text-slate-950 font-bold"
                    : "bg-slate-800 text-slate-400"
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-80">
          <div className="pointer-events-none absolute inset-y-0 start-0 flex items-center ps-3 text-slate-500">
            <Search className="w-3.5 h-3.5" />
          </div>
          <input
            type="text"
            value={formSearchQuery}
            onChange={(e) => setFormSearchQuery(e.target.value)}
            placeholder="Search forms..."
            className="w-full rounded-xl border border-slate-800 bg-[#0A0E17] py-1.5 ps-8 pe-3 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 transition-all"
          />
        </div>
      </div>

      {/* Row 2: Category Filter Pills + Auto-Categorize Button */}
      {(categories.length > 0 || categoryCounts.uncategorized > 0) && (
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800">
          <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto py-0.5">
            <span className="text-[11px] font-semibold text-slate-400 mr-1 flex items-center gap-1">
              <Folder className="w-3 h-3" /> Category:
            </span>
            <button
              type="button"
              onClick={() => setCategoryFilter("all")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-all cursor-pointer ${
                categoryFilter === "all"
                  ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-400 shadow-xs font-bold"
                  : "bg-[#0F1522] text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800"
              }`}
            >
              <span>All Categories</span>
              <span
                className={`text-[10px] font-mono px-1 rounded-full ${
                  categoryFilter === "all"
                    ? "bg-emerald-500/30 text-emerald-300 font-bold"
                    : "bg-slate-800 text-slate-400"
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
                      ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-400 shadow-xs font-bold"
                      : "bg-[#0F1522] text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800"
                  }`}
                >
                  <CategoryIcon icon={cat.icon} className="w-3.5 h-3.5 shrink-0" />
                  <span>{cat.name}</span>
                  <span
                    className={`text-[10px] font-mono px-1 rounded-full ${
                      isSelected
                        ? "bg-emerald-500/30 text-emerald-300 font-bold"
                        : "bg-slate-800 text-slate-400"
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
                    ? "bg-amber-500/20 border-amber-500/50 text-amber-300 shadow-xs font-bold"
                    : "bg-[#0F1522] text-amber-400 hover:bg-slate-800 border border-amber-500/30"
                }`}
              >
                <Tag className="w-3 h-3 text-amber-400" />
                <span>Uncategorized</span>
                <span
                  className={`text-[10px] font-mono px-1 rounded-full ${
                    categoryFilter === "uncategorized"
                      ? "bg-amber-500/30 text-amber-200 font-bold"
                      : "bg-slate-800 text-amber-400"
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
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-xs font-semibold shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
              title="Automatically match official forms to categories based on keywords"
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
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
            <div key={i} className="h-44 rounded-2xl bg-[#0F1522] border border-slate-800 animate-pulse" />
          ))}
        </div>
      ) : filteredForms.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-[#0F1522] p-12 text-center shadow-card">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <FileText className="w-6 h-6" />
          </div>
          <h3 className="mt-3 text-sm font-bold text-white">
            No official forms found
          </h3>
          <p className="mt-1 text-xs text-slate-400 max-w-sm mx-auto">
            Upload your organization’s official blank PDF forms to auto-detect fields and create interactive multilingual workflows.
          </p>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-2.5">
            {forms.length === 0 && (
              <button
                type="button"
                disabled={isProvisioningStarters}
                onClick={async () => {
                  setIsProvisioningStarters(true);
                  try {
                    const res = await provisionStarterTemplates();
                    const updated = await listOrganizationForms();
                    setForms(updated);
                    if (res.provisionedCount > 0) {
                      setCategoryToast(
                        `Loaded ${res.provisionedCount} ready-to-send starter templates.`
                      );
                    }
                  } catch (err) {
                    setCategoryToast(
                      err instanceof Error
                        ? err.message
                        : "Failed to load starter templates."
                    );
                  } finally {
                    setIsProvisioningStarters(false);
                  }
                }}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800 hover:border-slate-600 transition-colors cursor-pointer disabled:opacity-50"
              >
                {isProvisioningStarters ? (
                  <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                ) : (
                  <Sparkles className="w-4 h-4 text-emerald-400" />
                )}
                Load 3 Starter Templates
              </button>
            )}
            <button
              type="button"
              onClick={() => setIsUploadFormOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-[0_0_20px_-3px_rgba(16,185,129,0.35)] active:scale-[0.98] transition-all cursor-pointer"
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
              className="rounded-2xl border border-slate-800 bg-[#0F1522] p-5 shadow-card hover:border-emerald-500/40 hover:shadow-[0_0_20px_rgba(16,185,129,0.15)] transition-all flex flex-col justify-between group relative overflow-hidden"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2.5">
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider border ${
                      f.status === "published"
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                        : f.status === "archived"
                        ? "border-slate-700 bg-slate-800/60 text-slate-400"
                        : "border-amber-500/30 bg-amber-500/10 text-amber-400"
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      f.status === "published" ? "bg-emerald-400" : f.status === "archived" ? "bg-slate-500" : "bg-amber-400"
                    }`} />
                    <span>
                      {f.status === "published" ? "PUBLISHED" : f.status === "needs_review" ? "Needs review" : f.status === "draft" ? "DRAFT" : "ARCHIVED"}
                    </span>
                  </span>
                  <span className="text-[11px] font-mono text-slate-500">
                    v{f.versionNumber}
                  </span>
                </div>

                <h3 className="text-sm font-bold text-white group-hover:text-emerald-400 line-clamp-1 transition-colors">
                  {f.name}
                </h3>
                <p className="text-[11px] font-mono text-slate-500 mt-0.5 truncate">{f.key}</p>

                <div className="mt-3.5 flex items-center justify-between gap-2 text-xs">
                  <span className="inline-flex items-center gap-1.5 text-[11px] text-slate-400 bg-slate-900 border border-slate-800 px-2.5 py-0.5 rounded-md font-mono">
                    <FileText className="w-3 h-3 text-slate-500" />
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
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-medium border transition-colors cursor-pointer ${
                        f.categoryId || f.category_id
                          ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20"
                          : "bg-slate-900/60 border-dashed border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                      }`}
                      title="Click to assign or change category"
                    >
                      <CategoryIcon
                        icon={f.categoryIcon || f.category_icon}
                        className="w-3 h-3 text-emerald-400"
                      />
                      <span className="truncate max-w-[120px]">
                        {f.categoryName || f.category_name || (f.category && f.category !== "general" ? f.category : "+ Categorize")}
                      </span>
                      <ChevronDown className="w-2.5 h-2.5 text-slate-500" />
                    </button>

                    {/* Popover Dropdown Menu */}
                    {activeCategoryMenuFormId === f.id && (
                      <div
                        onClick={(e) => e.stopPropagation()}
                        className="absolute right-0 bottom-full mb-1 z-30 w-56 rounded-xl border border-slate-800 bg-[#0F1522] p-1.5 shadow-xl text-slate-200"
                      >
                        <div className="px-2 py-1 text-[10px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
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
                                    ? "bg-emerald-500/20 text-emerald-300 font-semibold"
                                    : "text-slate-300 hover:bg-slate-800"
                                }`}
                              >
                                <span className="flex items-center gap-2 truncate">
                                  <CategoryIcon
                                    icon={cat.icon}
                                    className="w-3.5 h-3.5 shrink-0 text-slate-400"
                                  />
                                  <span className="truncate">{cat.name}</span>
                                </span>
                                {isSelected && (
                                  <Check className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                                )}
                              </button>
                            );
                          })}
                        </div>
                        <div className="mt-1 pt-1 border-t border-slate-800">
                          <button
                            type="button"
                            onClick={() => handleQuickUpdateCategory(f.id, null)}
                            className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200 cursor-pointer"
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

              <div className="mt-4 pt-3.5 border-t border-slate-800 flex items-center justify-between gap-2">
                <span className="text-[11px] font-mono text-slate-500 truncate">
                  {new Date(f.updatedAt).toLocaleDateString()}
                </span>
                <div className="flex items-center gap-1.5 shrink-0">
                  {f.status === "published" && (
                    <button
                      type="button"
                      onClick={() => setSharingForm(f)}
                      className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg border border-slate-700 bg-slate-800/80 text-[11px] font-medium text-slate-200 hover:bg-slate-800 hover:border-slate-600 transition-colors cursor-pointer"
                      title="Share Form & Counter QR Code"
                    >
                      <QrCode className="w-3 h-3 text-slate-400" />
                      <span>Share</span>
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setSelectedTemplateIdForReview(f.id)}
                    className="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-[11px] font-semibold text-emerald-400 hover:bg-emerald-500/20 transition-colors cursor-pointer"
                    title="Review Schema & PDF Layout"
                  >
                    <Layers className="w-3 h-3 text-emerald-400" />
                    <span>Review</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteForm(f.id, f.name)}
                    className="h-7 w-7 inline-flex items-center justify-center rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
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

  const renderCasesWorkspace = () => {
    const invitedCount = cases.filter((c) => c.status === "invited").length;
    const inProgressCount = cases.filter((c) => c.status === "in_progress").length;
    const completedCount = cases.filter(
      (c) => c.status === "awaiting_review" || c.status === "completed"
    ).length;

    return (
      <div className="space-y-5" data-testid="portal-cases-workspace">
        {/* Candidate Intakes Summary Strip */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-2xl border border-slate-800 border-t-2 border-t-emerald-500/60 bg-[#0F1522] p-4 sm:p-5 shadow-card">
            <div className="text-xs font-medium text-slate-400">Total Intakes</div>
            <div className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-mono">
              {cases.length}
            </div>
            <div className="mt-1 text-[11px] font-mono text-slate-500">ALL CANDIDATES</div>
          </div>
          <div className="rounded-2xl border border-slate-800 border-t-2 border-t-amber-500 bg-[#0F1522] p-4 sm:p-5 shadow-card">
            <div className="text-xs font-medium text-slate-400">Invited</div>
            <div className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-amber-400 font-mono">
              {invitedCount}
            </div>
            <div className="mt-1 text-[11px] font-mono text-amber-400/80">AWAITING OTP</div>
          </div>
          <div className="rounded-2xl border border-slate-800 border-t-2 border-t-emerald-500 bg-[#0F1522] p-4 sm:p-5 shadow-card">
            <div className="text-xs font-medium text-slate-400">In Progress</div>
            <div className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-emerald-400 font-mono">
              {inProgressCount}
            </div>
            <div className="mt-1 text-[11px] font-mono text-emerald-400/80">EMAIL VERIFIED</div>
          </div>
          <div className="rounded-2xl border border-slate-800 border-t-2 border-t-slate-600 bg-[#0F1522] p-4 sm:p-5 shadow-card">
            <div className="text-xs font-medium text-slate-400">Completed / Review</div>
            <div className="mt-2 text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-mono">
              {completedCount}
            </div>
            <div className="mt-1 text-[11px] font-mono text-slate-500">READY</div>
          </div>
        </div>

        {/* Filter & Action Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: "all", label: "All" },
              { id: "invited", label: "Invited" },
              { id: "in_progress", label: "In Progress" },
              { id: "awaiting_review", label: "Awaiting Review" },
              { id: "completed", label: "Completed" },
              { id: "revoked", label: "Revoked" },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setCaseStatusFilter(tab.id)}
                className={`rounded-xl px-3 py-1.5 text-xs font-medium transition-all cursor-pointer ${
                  caseStatusFilter === tab.id
                    ? "bg-emerald-500 text-slate-950 font-bold"
                    : "bg-[#0F1522] text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-72">
              <div className="pointer-events-none absolute inset-y-0 start-0 flex items-center ps-3 text-slate-500">
                <Search className="w-3.5 h-3.5" />
              </div>
              <input
                type="text"
                value={caseSearchQuery}
                onChange={(e) => setCaseSearchQuery(e.target.value)}
                placeholder="Search candidates, emails, or forms..."
                className="w-full rounded-xl border border-slate-800 bg-[#0A0E17] py-1.5 ps-8 pe-3 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>
            <button
              type="button"
              onClick={fetchCases}
              disabled={loadingCases}
              className="rounded-xl border border-slate-800 bg-[#0F1522] px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition-colors cursor-pointer disabled:opacity-50"
            >
              {loadingCases ? "Loading..." : "Refresh"}
            </button>
          </div>
        </div>

        {caseActionError && (
          <div
            role="alert"
            className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-xs text-rose-200 flex items-center justify-between gap-2"
          >
            <span>{caseActionError}</span>
            <button
              type="button"
              onClick={() => setCaseActionError(null)}
              className="text-rose-300 hover:text-white font-bold cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {filteredCases.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-[#0F1522] p-10 text-center shadow-card">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <Users className="w-6 h-6" />
            </div>
            <h3 className="mt-3 text-sm font-bold text-white">
              No candidate intakes found
            </h3>
            <p className="mt-1 text-xs text-slate-400 max-w-sm mx-auto">
              Send a private, email-verified form invite to an applicant in any of 8 languages.
            </p>
            <button
              type="button"
              onClick={() => setIsNewCaseModalOpen(true)}
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-emerald-400 transition-colors cursor-pointer"
            >
              <UserPlus className="w-4 h-4" />
              <span>New Intake</span>
            </button>
          </div>
        ) : (
          <div className="rounded-2xl border border-slate-800 bg-[#0F1522] overflow-hidden shadow-card">
            <div className="divide-y divide-slate-800">
              {filteredCases.map((c) => {
                const isBusy = caseActionLoadingId === c.public_id;
                const statusBadge =
                  c.status === "revoked"
                    ? "border-rose-500/30 bg-rose-500/10 text-rose-300"
                    : c.status === "completed" || c.status === "awaiting_review"
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                    : c.status === "in_progress"
                    ? "border-sky-500/30 bg-sky-500/10 text-sky-300"
                    : "border-amber-500/30 bg-amber-500/10 text-amber-300";

                const statusLabel =
                  c.status === "revoked"
                    ? "Revoked"
                    : c.status === "awaiting_review"
                    ? "Awaiting Review"
                    : c.status === "in_progress"
                    ? "In Progress"
                    : c.status === "completed"
                    ? "Completed"
                    : "Invited";

                return (
                  <div
                    key={c.public_id}
                    data-testid={`case-row-${c.public_id}`}
                    className="p-4 sm:p-5 flex flex-col lg:flex-row lg:items-center justify-between gap-4 hover:bg-[#151D2E]/50 transition-colors"
                  >
                    <div className="min-w-0 space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-white truncate">
                          {c.candidate_name}
                        </span>
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider ${statusBadge}`}
                        >
                          {statusLabel}
                        </span>
                        {c.otp_verified_at && c.status !== "revoked" && (
                          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                            <KeyRound className="w-3 h-3" />
                            Email Verified
                          </span>
                        )}
                        {(c.resend_count || 0) > 0 && (
                          <span className="text-[10px] font-mono text-slate-400">
                            Resent {c.resend_count}x
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400">
                        <bdi className="font-mono text-slate-300">
                          {c.candidate_email}
                        </bdi>
                        <span>•</span>
                        <span className="text-slate-300">
                          {c.form_title || c.form_version_id}
                        </span>
                      </div>

                      {c.notes && (
                        <p className="text-xs text-slate-500 truncate">
                          {c.notes}
                        </p>
                      )}
                    </div>

                    <div className="flex flex-col sm:flex-row sm:items-center gap-4 shrink-0">
                      <div className="w-40 space-y-1">
                        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                          <span>Progress</span>
                          <span className="text-white font-bold">
                            {c.answered_fields}/{c.total_fields} ({c.progress_percent}%)
                          </span>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-emerald-500 transition-all"
                            style={{ width: `${c.progress_percent}%` }}
                          />
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          data-testid={`resend-case-${c.public_id}`}
                          disabled={c.status === "completed" || isBusy}
                          onClick={() => handleResendCase(c.public_id)}
                          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-40 transition-colors cursor-pointer"
                        >
                          {isBusy ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Send className="w-3.5 h-3.5 text-emerald-400" />
                          )}
                          <span>Resend Link</span>
                        </button>

                        {c.status !== "revoked" && c.status !== "completed" && (
                          <button
                            type="button"
                            data-testid={`revoke-case-${c.public_id}`}
                            disabled={isBusy}
                            onClick={() => handleRevokeCase(c.public_id)}
                            className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 disabled:opacity-40 transition-colors cursor-pointer"
                          >
                            <Ban className="w-3.5 h-3.5" />
                            <span>Revoke</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      className={`mx-auto max-w-7xl px-4 ${
        isCompact ? "py-4 sm:px-4 space-y-4" : "py-8 sm:px-6 lg:px-8 space-y-6"
      }`}
    >
      {(theme.section_order || ["header", "metrics", "actions", "forms"]).map((sec) => {
        if (sec === "header") return <React.Fragment key="header">{renderHeader()}</React.Fragment>;
        if (activeWorkspaceTab === "forms") {
          if (sec === "metrics") return <React.Fragment key="metrics">{renderMetrics()}</React.Fragment>;
          if (sec === "actions") return <React.Fragment key="actions">{renderActions()}</React.Fragment>;
          if (sec === "forms") return <React.Fragment key="forms">{renderForms()}</React.Fragment>;
        }
        return null;
      })}

      {activeWorkspaceTab === "cases" && renderCasesWorkspace()}

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

      {isNewCaseModalOpen && (
        <NewCaseModal
          isOpen={isNewCaseModalOpen}
          onClose={() => setIsNewCaseModalOpen(false)}
          onCaseCreated={(newCase) => {
            setCases((prev) => [newCase, ...prev]);
            setCreatedOrResentCase(newCase);
            setActiveWorkspaceTab("cases");
          }}
        />
      )}

      {createdOrResentCase && (
        <InviteSuccessModal
          caseData={createdOrResentCase}
          onClose={() => setCreatedOrResentCase(null)}
        />
      )}
    </div>
  );
}
