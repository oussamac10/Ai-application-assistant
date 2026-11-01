"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  getCurrentOrganization,
  listCases,
  listOrganizationForms,
  deleteForm,
} from "../services/portalClient";
import {
  Case,
  CaseStatus,
  Organization,
  OrganizationFormSummary,
} from "../types";
import { NewCaseModal } from "./NewCaseModal";
import { InviteSuccessModal } from "./InviteSuccessModal";
import { FormUploadModal } from "./FormUploadModal";
import { FormSchemaReviewStudio } from "./FormSchemaReviewStudio";
import {
  CheckCircle2,
  FileText,
  ShieldCheck,
  UploadCloud,
  Layers,
  ArrowRight,
  ExternalLink,
  Sparkles,
  Trash2,
} from "lucide-react";

export function PortalDashboard() {
  const t = useTranslations("portal");

  const [activeTab, setActiveTab] = useState<"cases" | "forms">("cases");
  const [org, setOrg] = useState<Organization | null>(null);
  const [cases, setCases] = useState<Case[]>([]);
  const [forms, setForms] = useState<OrganizationFormSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingForms, setLoadingForms] = useState(false);

  // Cases filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [isNewCaseOpen, setIsNewCaseOpen] = useState(false);
  const [createdCaseForInvite, setCreatedCaseForInvite] = useState<Case | null>(null);
  const [copiedCaseId, setCopiedCaseId] = useState<string | null>(null);

  // Forms state
  const [formSearchQuery, setFormSearchQuery] = useState("");
  const [formStatusFilter, setFormStatusFilter] = useState<string>("all");
  const [isUploadFormOpen, setIsUploadFormOpen] = useState(false);
  const [selectedTemplateIdForReview, setSelectedTemplateIdForReview] = useState<string | null>(null);

  const fetchWorkspace = () => {
    setLoading(true);
    Promise.all([
      getCurrentOrganization(),
      listCases(),
      listOrganizationForms().catch(() => []),
    ])
      .then(([orgData, casesData, formsData]) => {
        setOrg(orgData);
        setCases(casesData);
        setForms(formsData);
      })
      .catch((err) => {
        console.error("Workspace load error:", err);
      })
      .finally(() => setLoading(false));
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

  useEffect(() => {
    fetchWorkspace();
  }, []);

  const stats = useMemo(() => {
    const total = cases.length;
    const inProgress = cases.filter((c) => c.status === "in_progress").length;
    const awaitingReview = cases.filter((c) => c.status === "awaiting_review").length;
    const completed = cases.filter((c) => c.status === "completed").length;
    return { total, inProgress, awaitingReview, completed };
  }, [cases]);

  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      if (statusFilter !== "all" && c.status !== statusFilter) {
        return false;
      }
      if (searchQuery.trim().length > 0) {
        const q = searchQuery.toLowerCase();
        const matchesName = c.candidate_name.toLowerCase().includes(q);
        const matchesEmail = c.candidate_email.toLowerCase().includes(q);
        const matchesForm = (c.form_title || "").toLowerCase().includes(q);
        return matchesName || matchesEmail || matchesForm;
      }
      return true;
    });
  }, [cases, statusFilter, searchQuery]);

  const formsNeedingReviewCount = useMemo(() => {
    return forms.filter((f) => f.status === "needs_review").length;
  }, [forms]);

  const filteredForms = useMemo(() => {
    return forms.filter((f) => {
      if (formStatusFilter !== "all" && f.status !== formStatusFilter) {
        return false;
      }
      if (formSearchQuery.trim().length > 0) {
        const q = formSearchQuery.toLowerCase();
        const matchesName = f.name.toLowerCase().includes(q);
        const matchesKey = f.key.toLowerCase().includes(q);
        const matchesCategory = (f.category || "").toLowerCase().includes(q);
        return matchesName || matchesKey || matchesCategory;
      }
      return true;
    });
  }, [forms, formStatusFilter, formSearchQuery]);

  const handleCopyLink = async (c: Case) => {
    if (!c.invite_token) {
      setCreatedCaseForInvite(c);
      return;
    }
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    const inviteUrl = `${origin}/portal/invite/${c.invite_token}`;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopiedCaseId(c.id);
      setTimeout(() => setCopiedCaseId(null), 2500);
    } catch {
      // Fallback
    }
  };

  const getStatusBadge = (status: CaseStatus) => {
    switch (status) {
      case "invited":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-800">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            {t("filterInvited")}
          </span>
        );
      case "in_progress":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-[#f7f6fe] px-2.5 py-0.5 text-[11px] font-semibold text-[#6551f3]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#6551f3]" />
            {t("filterInProgress")}
          </span>
        );
      case "awaiting_review":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-200 bg-purple-50 px-2.5 py-0.5 text-[11px] font-semibold text-purple-700">
            <span className="h-1.5 w-1.5 rounded-full bg-purple-500 animate-pulse" />
            {t("filterReview")}
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-[#e6f9f2] px-2.5 py-0.5 text-[11px] font-semibold text-[#00c07d]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#00c07d]" />
            {t("filterCompleted")}
          </span>
        );
      default:
        return null;
    }
  };

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

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Aikido Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-[#737283] font-medium mb-3">
        <span className="font-semibold text-slate-800">Workspaces</span>
        <span className="text-slate-300">/</span>
        <span className="text-slate-800 font-semibold truncate max-w-xs">Agency Hub</span>
        <span className="text-slate-300">/</span>
        <span className="text-[#6551f3] font-bold">Triage Queue</span>
      </div>

      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-[#ebecf0]">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-[#010024] sm:text-3xl">
              {org?.name || t("title")}
            </h1>
            {org?.is_verified_government && (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-[#e6f9f2] px-2.5 py-0.5 text-xs font-semibold text-[#00c07d]">
                <ShieldCheck className="w-3.5 h-3.5 text-[#00c07d]" />
                Verified Government
              </span>
            )}
            {org?.verification_status === "pending_review" && !org?.is_verified_government && (
              <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700">
                Verification Pending
              </span>
            )}
            <span className="rounded-lg border border-[#e0dcfd] bg-[#f7f6fe] px-2.5 py-0.5 text-xs font-bold text-[#6551f3] uppercase font-mono">
              {org?.organization_type ? org.organization_type.replace(/_/g, " ") : "Official Workspace"}
            </span>
          </div>
          <p className="mt-1.5 text-sm text-[#737283] max-w-2xl">
            {t("subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          {activeTab === "cases" ? (
            <button
              type="button"
              onClick={() => setIsNewCaseOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#6551f3] px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#523ee8] active:bg-[#3d3192] transition-all"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
              </svg>
              <span>{t("newCase")}</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setIsUploadFormOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#6551f3] px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#523ee8] active:bg-[#3d3192] transition-all"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>Upload Official PDF</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Workspace Aikido Pill Segmented Control */}
      <div className="mt-6 flex">
        <div className="inline-flex items-center p-1 bg-slate-100 rounded-xl border border-[#ebecf0]">
          <button
            type="button"
            onClick={() => setActiveTab("cases")}
            className={`px-3.5 py-1.5 text-xs font-bold rounded-lg flex items-center gap-2 transition-all ${
              activeTab === "cases"
                ? "bg-white text-[#010024] shadow-xs"
                : "text-[#737283] hover:text-[#010024]"
            }`}
          >
            <span>Citizen Intake Queue</span>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-mono font-bold ${
              activeTab === "cases" ? "bg-[#f7f6fe] text-[#6551f3]" : "bg-slate-200 text-[#737283]"
            }`}>
              {cases.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("forms")}
            className={`px-3.5 py-1.5 text-xs font-bold rounded-lg flex items-center gap-2 transition-all ${
              activeTab === "forms"
                ? "bg-white text-[#010024] shadow-xs"
                : "text-[#737283] hover:text-[#010024]"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Official Forms & Review Studio</span>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-mono font-bold ${
              activeTab === "forms" ? "bg-[#f7f6fe] text-[#6551f3]" : "bg-slate-200 text-[#737283]"
            }`}>
              {forms.length}
            </span>
            {formsNeedingReviewCount > 0 && (
              <span className="rounded-full bg-amber-100 text-amber-800 px-1.5 py-0.2 font-mono text-[10px] font-bold">
                {formsNeedingReviewCount} review
              </span>
            )}
          </button>
        </div>
      </div>

      {/* TAB 1: CASES MANAGEMENT */}
      {activeTab === "cases" && (
        <>
          {/* High-Density Metrics Strip (Aikido Style) */}
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-[#ebecf0] bg-white p-4 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-[#737283] uppercase tracking-wider">
                  {t("totalCases")}
                </span>
                <span className="h-2 w-2 rounded-full bg-slate-400" />
              </div>
              <div className="mt-2 text-2xl font-extrabold font-mono text-[#010024]">{stats.total}</div>
            </div>
            <div className="rounded-xl border border-[#ebecf0] bg-white p-4 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-[#737283] uppercase tracking-wider">
                  {t("inProgress")}
                </span>
                <span className="h-2 w-2 rounded-full bg-[#6551f3]" />
              </div>
              <div className="mt-2 text-2xl font-extrabold font-mono text-[#6551f3]">{stats.inProgress}</div>
            </div>
            <div className="rounded-xl border border-[#ebecf0] bg-white p-4 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-[#737283] uppercase tracking-wider">
                  {t("awaitingReview")}
                </span>
                <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
              </div>
              <div className="mt-2 text-2xl font-extrabold font-mono text-amber-700">{stats.awaitingReview}</div>
            </div>
            <div className="rounded-xl border border-[#ebecf0] bg-white p-4 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-[#737283] uppercase tracking-wider">
                  {t("completed")}
                </span>
                <span className="h-2 w-2 rounded-full bg-[#00c07d]" />
              </div>
              <div className="mt-2 text-2xl font-extrabold font-mono text-[#00c07d]">{stats.completed}</div>
            </div>
          </div>

          {/* Aikido Filter and Search Bar */}
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
              {[
                { id: "all", label: t("filterAll"), count: stats.total },
                { id: "invited", label: t("filterInvited"), count: cases.filter(c => c.status === "invited").length },
                { id: "in_progress", label: t("filterInProgress"), count: stats.inProgress },
                { id: "awaiting_review", label: t("filterReview"), count: stats.awaitingReview },
                { id: "completed", label: t("filterCompleted"), count: stats.completed },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setStatusFilter(tab.id)}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                    statusFilter === tab.id
                      ? "bg-[#010024] text-white shadow-2xs"
                      : "bg-white text-[#737283] hover:text-[#010024] hover:bg-[#f7f6fe] border border-[#ebecf0]"
                  }`}
                >
                  <span>{tab.label}</span>
                  <span
                    className={`font-mono text-[10px] rounded-full px-1.5 py-0.2 ${
                      statusFilter === tab.id
                        ? "bg-white/20 text-white"
                        : "bg-slate-100 text-[#737283]"
                    }`}
                  >
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>

            <div className="relative w-full sm:w-80">
              <div className="pointer-events-none absolute inset-y-0 start-0 flex items-center ps-3 text-[#737283]">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("searchPlaceholder")}
                className="w-full rounded-lg border border-[#ebecf0] bg-white py-1.5 ps-8 pe-12 text-xs text-[#010024] placeholder-[#737283] focus:border-[#6551f3] focus:outline-none focus:ring-2 focus:ring-[#6551f3]/15 transition-all"
              />
              <div className="pointer-events-none absolute inset-y-0 end-0 flex items-center pe-2.5">
                <kbd className="rounded border border-[#ebecf0] bg-[#f9f9fb] px-1.5 py-0.5 font-mono text-[9px] font-bold text-[#737283]">
                  ⌘K
                </kbd>
              </div>
            </div>
          </div>

          {/* Aikido Data Table */}
          <div className="mt-4 overflow-hidden rounded-xl border border-[#ebecf0] bg-white shadow-2xs">
            {filteredCases.length === 0 ? (
              <div className="p-12 text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f7f6fe] border border-[#e0dcfd] text-[#6551f3]">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="mt-3 text-sm font-bold text-[#010024]">{t("emptyCases")}</h3>
                <p className="mt-1 text-xs text-[#737283]">{t("emptyCasesSub")}</p>
                <div className="mt-5">
                  <button
                    type="button"
                    onClick={() => setIsNewCaseOpen(true)}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-[#6551f3] px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#523ee8] transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                    </svg>
                    <span>{t("newCase")}</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-start text-xs border-collapse">
                  <thead className="border-b border-[#ebecf0] bg-[#f9f9fb] text-[#737283] uppercase tracking-wider font-bold text-[10px]">
                    <tr>
                      <th scope="col" className="px-4 py-3 text-start">{t("candidate")}</th>
                      <th scope="col" className="px-4 py-3 text-start">{t("template")}</th>
                      <th scope="col" className="px-4 py-3 text-start">{t("status")}</th>
                      <th scope="col" className="px-4 py-3 text-start">{t("progress")}</th>
                      <th scope="col" className="px-4 py-3 text-start">{t("created")}</th>
                      <th scope="col" className="px-4 py-3 text-end">{t("actions")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#ebecf0]">
                    {filteredCases.map((c) => {
                      const initials = c.candidate_name
                        .split(" ")
                        .map((part) => part[0])
                        .join("")
                        .slice(0, 2)
                        .toUpperCase();

                      return (
                        <tr
                          key={c.id}
                          className="hover:bg-[#f7f6fe] transition-colors duration-150 group"
                        >
                          <td className="px-4 py-3 whitespace-nowrap">
                            <div className="flex items-center gap-2.5">
                              <div className="w-7 h-7 rounded-full bg-[#f7f6fe] border border-[#e0dcfd] text-[#6551f3] text-[10px] font-bold flex items-center justify-center shrink-0">
                                {initials || "U"}
                              </div>
                              <div>
                                <div className="font-bold text-[#010024] text-xs group-hover:text-[#6551f3] transition-colors">
                                  {c.candidate_name}
                                </div>
                                <div className="text-[11px] text-[#737283] font-mono">
                                  {c.candidate_email}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="font-medium text-[#010024] line-clamp-1 max-w-xs text-xs">
                              {c.form_title || "Official Administrative Template"}
                            </div>
                            {c.notes && (
                              <div className="text-[10px] text-[#737283] italic line-clamp-1">
                                {c.notes}
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            {getStatusBadge(c.status)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              <div className="w-20 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                                <div
                                  className={`h-full rounded-full transition-all duration-300 ${
                                    c.progress_percent === 100
                                      ? "bg-[#00c07d]"
                                      : "bg-[#6551f3]"
                                  }`}
                                  style={{ width: `${c.progress_percent}%` }}
                                />
                              </div>
                              <span className="font-mono text-[11px] font-bold text-slate-700">
                                {c.progress_percent}%
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-[#737283] font-mono text-[11px]">
                            {new Date(c.created_at).toLocaleDateString()}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-end">
                            <div className="inline-flex items-center gap-2 justify-end">
                              {c.invite_token && (
                                <button
                                  type="button"
                                  onClick={() => handleCopyLink(c)}
                                  className="inline-flex items-center gap-1 rounded-full border border-[#ebecf0] bg-white px-2.5 py-1 text-[11px] font-medium text-[#737283] hover:border-[#e0dcfd] hover:text-[#6551f3] transition-colors"
                                >
                                  {copiedCaseId === c.id ? (
                                    <span className="text-[#00c07d] font-bold">{t("copied")}</span>
                                  ) : (
                                    <span>{t("copyInvite")}</span>
                                  )}
                                </button>
                              )}
                              {c.session_public_id && (
                                <Link
                                  href={`/application/session/${c.session_public_id}`}
                                  className="inline-flex items-center gap-1 rounded-full bg-[#f7f6fe] border border-[#e0dcfd] px-3 py-1 text-[11px] font-bold text-[#6551f3] hover:bg-[#e0dcfd] transition-colors"
                                >
                                  <span>{t("reviewInStudio")}</span>
                                  <ArrowRight className="w-3 h-3" />
                                </Link>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* TAB 2: FORMS & HUMAN SCHEMA REVIEW STUDIO */}
      {activeTab === "forms" && (
        <div className="mt-6 space-y-5">
          {/* Aikido Forms Metric Cards */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-[#ebecf0] bg-white p-4 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-[#737283] uppercase tracking-wider">
                  Total Official Forms
                </span>
                <span className="h-2 w-2 rounded-full bg-slate-400" />
              </div>
              <div className="mt-2 text-2xl font-extrabold font-mono text-[#010024]">{forms.length}</div>
            </div>
            <div className="rounded-xl border border-[#ebecf0] bg-white p-4 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-[#737283] uppercase tracking-wider">
                  Live in Portal
                </span>
                <span className="h-2 w-2 rounded-full bg-[#00c07d]" />
              </div>
              <div className="mt-2 text-2xl font-extrabold font-mono text-[#00c07d]">
                {forms.filter((f) => f.status === "published").length}
              </div>
            </div>
            <div className="rounded-xl border border-[#ebecf0] bg-white p-4 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-[#737283] uppercase tracking-wider">
                  Needs Review
                </span>
                <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
              </div>
              <div className="mt-2 text-2xl font-extrabold font-mono text-amber-700">
                {formsNeedingReviewCount}
              </div>
            </div>
            <div className="rounded-xl border border-[#ebecf0] bg-white p-4 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-[#737283] uppercase tracking-wider">
                  Archived
                </span>
                <span className="h-2 w-2 rounded-full bg-slate-300" />
              </div>
              <div className="mt-2 text-2xl font-extrabold font-mono text-slate-500">
                {forms.filter((f) => f.status === "archived").length}
              </div>
            </div>
          </div>

          {/* Forms Filter & Search */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
              {[
                { id: "all", label: "All Forms", count: forms.length },
                { id: "needs_review", label: "Needs Review", count: formsNeedingReviewCount },
                { id: "published", label: "Published", count: forms.filter((f) => f.status === "published").length },
                { id: "archived", label: "Archived", count: forms.filter((f) => f.status === "archived").length },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setFormStatusFilter(tab.id)}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                    formStatusFilter === tab.id
                      ? "bg-[#010024] text-white shadow-2xs"
                      : "bg-white text-[#737283] hover:text-[#010024] hover:bg-[#f7f6fe] border border-[#ebecf0]"
                  }`}
                >
                  <span>{tab.label}</span>
                  <span
                    className={`font-mono text-[10px] rounded-full px-1.5 py-0.2 ${
                      formStatusFilter === tab.id
                        ? "bg-white/20 text-white"
                        : "bg-slate-100 text-[#737283]"
                    }`}
                  >
                    {tab.count}
                  </span>
                </button>
              ))}
            </div>

            <div className="relative w-full sm:w-80">
              <div className="pointer-events-none absolute inset-y-0 start-0 flex items-center ps-3 text-[#737283]">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                value={formSearchQuery}
                onChange={(e) => setFormSearchQuery(e.target.value)}
                placeholder="Search official forms or departments..."
                className="w-full rounded-lg border border-[#ebecf0] bg-white py-1.5 ps-8 pe-3 text-xs text-[#010024] placeholder-[#737283] focus:border-[#6551f3] focus:outline-none focus:ring-2 focus:ring-[#6551f3]/15 transition-all"
              />
            </div>
          </div>

          {/* Forms List Grid / Table */}
          {loadingForms ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-44 rounded-2xl bg-slate-100 animate-pulse" />
              ))}
            </div>
          ) : filteredForms.length === 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-2xs">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="mt-3 text-sm font-bold text-slate-900">
                No official forms found
              </h3>
              <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
                Upload your municipality’s official blank PDF forms to auto-detect fields and create interactive multilingual workflows.
              </p>
              <div className="mt-5">
                <button
                  type="button"
                  onClick={() => setIsUploadFormOpen(true)}
                  className="inline-flex items-center gap-2 rounded-lg bg-[#6551f3] px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-[#523ee8] transition-colors"
                >
                  <UploadCloud className="w-4 h-4" /> Upload First Form
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredForms.map((f) => (
                <div
                  key={f.id}
                  className="rounded-xl border border-[#ebecf0] bg-white p-4 shadow-2xs hover:border-[#e0dcfd] hover:bg-[#f7f6fe]/30 transition-all flex flex-col justify-between group"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          f.status === "published"
                            ? "border border-emerald-200 bg-[#e6f9f2] text-[#00c07d]"
                            : f.status === "archived"
                            ? "border border-slate-200 bg-slate-100 text-[#737283]"
                            : "border border-amber-200 bg-amber-50 text-amber-800"
                        }`}
                      >
                        {f.status === "published" ? "Live in Portal" : f.status === "needs_review" ? "Needs Review" : "Archived"}
                      </span>
                      <span className="text-[11px] font-mono text-[#737283]">
                        v{f.versionNumber}
                      </span>
                    </div>

                    <h3 className="text-xs font-bold text-[#010024] group-hover:text-[#6551f3] line-clamp-1 transition-colors">{f.name}</h3>
                    <p className="text-[10px] font-mono text-[#737283] mt-0.5">{f.key}</p>

                    <div className="mt-3 space-y-1 text-xs text-[#737283]">
                      <div className="flex items-center justify-between text-[11px]">
                        <span>Fields Detected:</span>
                        <span className="font-mono font-bold text-[#6551f3]">{f.fieldsCount}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-[#ebecf0] flex items-center justify-between">
                    <span className="text-[10px] font-mono text-[#737283]">
                      Updated {new Date(f.updatedAt).toLocaleDateString()}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setSelectedTemplateIdForReview(f.id)}
                        className="inline-flex items-center gap-1 rounded-full bg-[#f7f6fe] border border-[#e0dcfd] px-2.5 py-1 text-[11px] font-bold text-[#6551f3] hover:bg-[#e0dcfd] transition-colors cursor-pointer"
                      >
                        <span>Review Schema & PDF</span>
                        <ArrowRight className="w-3 h-3" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteForm(f.id, f.name)}
                        className="p-1 rounded-full text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
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
      )}

      {/* Modals */}
      <NewCaseModal
        isOpen={isNewCaseOpen}
        onClose={() => setIsNewCaseOpen(false)}
        onCaseCreated={(newCase) => {
          setCases((prev) => [newCase, ...prev]);
          if (newCase.invite_token) {
            setCreatedCaseForInvite(newCase);
          }
        }}
      />

      <InviteSuccessModal
        caseData={createdCaseForInvite}
        onClose={() => setCreatedCaseForInvite(null)}
      />

      <FormUploadModal
        isOpen={isUploadFormOpen}
        onClose={() => setIsUploadFormOpen(false)}
        onFormUploaded={(reviewDetail) => {
          setIsUploadFormOpen(false);
          fetchForms();
          setSelectedTemplateIdForReview(reviewDetail.templateId);
        }}
      />
    </div>
  );
}
