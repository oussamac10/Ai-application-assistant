"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  getCurrentOrganization,
  listOrganizationForms,
  deleteForm,
} from "../services/portalClient";
import {
  Organization,
  OrganizationFormSummary,
} from "../types";
import { FormUploadModal } from "./FormUploadModal";
import { FormSchemaReviewStudio } from "./FormSchemaReviewStudio";
import { ShareFormModal } from "./ShareFormModal";
import {
  FileText,
  ShieldCheck,
  UploadCloud,
  Layers,
  Trash2,
  QrCode,
} from "lucide-react";

export function PortalDashboard() {
  const [org, setOrg] = useState<Organization | null>(null);
  const [forms, setForms] = useState<OrganizationFormSummary[]>([]);
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
    ])
      .then(([orgData, formsData]) => {
        setOrg(orgData);
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
      {/* Workspace Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-slate-500 font-medium mb-3">
        <span className="hover:text-slate-700 cursor-pointer">Workspaces</span>
        <span className="text-slate-300">/</span>
        <span className="text-slate-600">Agency Hub</span>
        <span className="text-slate-300">/</span>
        <span className="text-indigo-600 font-semibold">Forms & Studio</span>
      </div>

      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              {org?.name || "Official Forms & Review Studio"}
            </h1>
            {org?.is_verified_government && (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                Verified
              </span>
            )}
            {org?.verification_status === "pending_review" && !org?.is_verified_government && (
              <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700">
                Pending Verification
              </span>
            )}
            <span className="rounded-full border border-indigo-100 bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 capitalize">
              {org?.organization_type ? org.organization_type.replace(/_/g, " ") : "Official"}
            </span>
          </div>
          <p className="mt-1.5 text-sm text-slate-500 max-w-2xl">
            Manage official forms, configure schema mappings, generate QR codes, and review completed submissions.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setIsUploadFormOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-indigo-700 active:scale-[0.98] transition-all cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload PDF</span>
          </button>
        </div>
      </div>

      {/* Forms & Studio Content */}
      <div className="mt-6 space-y-5">
        {/* Forms Metric Cards */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">
                Total forms
              </span>
              <span className="h-2 w-2 rounded-full bg-slate-300" />
            </div>
            <div className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{forms.length}</div>
          </div>
          <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">
                Live in portal
              </span>
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
            </div>
            <div className="mt-2 text-2xl font-bold tracking-tight text-emerald-600">
              {forms.filter((f) => f.status === "published").length}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">
                Needs review
              </span>
              <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
            </div>
            <div className="mt-2 text-2xl font-bold tracking-tight text-amber-700">
              {formsNeedingReviewCount}
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200/90 bg-white p-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">
                Archived
              </span>
              <span className="h-2 w-2 rounded-full bg-slate-300" />
            </div>
            <div className="mt-2 text-2xl font-bold tracking-tight text-slate-500">
              {forms.filter((f) => f.status === "archived").length}
            </div>
          </div>
        </div>

        {/* Forms Filter & Search */}
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
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
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
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-indigo-700 transition-colors cursor-pointer"
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

                  <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                    <span className="inline-flex items-center gap-1 text-[11px] text-slate-600 bg-slate-50 border border-slate-200/80 px-2 py-0.5 rounded-md">
                      <FileText className="w-3 h-3 text-slate-400" />
                      <span>{f.fieldsCount} {f.fieldsCount === 1 ? "field" : "fields"}</span>
                    </span>
                    {f.category && (
                      <span className="text-[11px] text-slate-400 capitalize">
                        • {f.category}
                      </span>
                    )}
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
