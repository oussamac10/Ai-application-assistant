"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  createCheckoutSession,
  createPortalSession,
  getCurrentOrganization,
  getSubscription,
  listCases,
} from "../services/portalClient";
import { Case, CaseStatus, Organization, SubscriptionInfo } from "../types";
import { NewCaseModal } from "./NewCaseModal";
import { InviteSuccessModal } from "./InviteSuccessModal";
import { CheckCircle2, FileText, Settings, ShieldCheck } from "lucide-react";

export function PortalDashboard() {
  const t = useTranslations("portal");

  const [org, setOrg] = useState<Organization | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [isNewCaseOpen, setIsNewCaseOpen] = useState(false);
  const [createdCaseForInvite, setCreatedCaseForInvite] = useState<Case | null>(null);
  const [copiedCaseId, setCopiedCaseId] = useState<string | null>(null);

  const fetchWorkspace = () => {
    setLoading(true);
    Promise.all([
      getCurrentOrganization(),
      listCases(),
      getSubscription().catch(() => null),
    ])
      .then(([orgData, casesData, subData]) => {
        setOrg(orgData);
        setCases(casesData);
        setSubscription(subData);
      })
      .catch((err) => {
        console.error("Workspace load error:", err);
      })
      .finally(() => setLoading(false));
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

  const handleCopyLink = async (c: Case) => {
    if (!c.invite_token) {
      // If token not in DTO, prompt or open modal
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

  const handleUpgradePro = async () => {
    if (!org) return;
    setUpgrading(true);
    try {
      const res = await createCheckoutSession(org.id, "agency_pro");
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to initiate upgrade";
      alert(message);
    } finally {
      setUpgrading(false);
    }
  };

  const handleManageBilling = async () => {
    if (!org) return;
    setUpgrading(true);
    try {
      const res = await createPortalSession(org.id);
      if (res.portal_url) {
        window.location.href = res.portal_url;
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to open billing portal";
      alert(message);
    } finally {
      setUpgrading(false);
    }
  };

  const getStatusBadge = (status: CaseStatus) => {
    switch (status) {
      case "invited":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 ring-1 ring-inset ring-amber-600/20">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            {t("filterInvited")}
          </span>
        );
      case "in_progress":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700 ring-1 ring-inset ring-blue-600/20">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
            {t("filterInProgress")}
          </span>
        );
      case "awaiting_review":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-50 px-2.5 py-1 text-xs font-semibold text-purple-700 ring-1 ring-inset ring-purple-600/20">
            <span className="h-1.5 w-1.5 rounded-full bg-purple-500" />
            {t("filterReview")}
          </span>
        );
      case "completed":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            {t("filterCompleted")}
          </span>
        );
      default:
        return null;
    }
  };

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
      {/* Workspace Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              {org?.name || t("title")}
            </h1>
            {org?.is_verified_government && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                Verified Government
              </span>
            )}
            {org?.verification_status === "pending_review" && !org?.is_verified_government && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-700 ring-1 ring-inset ring-amber-600/20">
                Verification Pending
              </span>
            )}
            <span className="rounded-lg border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-xs font-bold text-indigo-700 uppercase">
              {(subscription?.plan_key || org?.billing_plan) === "enterprise"
                ? "Enterprise"
                : (subscription?.plan_key || org?.billing_plan) === "agency_pro"
                ? "Agency Pro • 50 Cases/mo"
                : "Agency Sandbox • 3 Cases/mo"}
            </span>
          </div>
          <p className="mt-1.5 text-sm text-slate-500 max-w-2xl">
            {t("subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Link
            href="/account"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition-colors"
          >
            <Settings className="w-3.5 h-3.5 text-slate-500" />
            <span>Workspace Settings</span>
          </Link>
          <button
            type="button"
            onClick={() => setIsNewCaseOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-xs hover:bg-indigo-700 active:scale-[0.99] transition-all"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
            </svg>
            {t("newCase")}
          </button>
        </div>
      </div>

      {/* Subscription & Case Quota Banner */}
      {subscription && (
        <div className="mt-6 rounded-2xl border border-indigo-100 bg-linear-to-r from-indigo-50/70 via-white to-slate-50 p-5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2.5">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-700 bg-indigo-100/70 px-2.5 py-0.5 rounded-full">
                {subscription.plan_key === "enterprise"
                  ? "Enterprise & Public Sector"
                  : subscription.plan_key === "agency_pro"
                  ? "Agency Pro"
                  : "Agency Sandbox (Evaluation)"}
              </span>
              <span className="text-xs text-slate-500 font-medium">
                {subscription.remaining_cases} cases remaining this period
              </span>
            </div>
            <div className="mt-2.5 flex items-center gap-3">
              <div className="h-2 w-full max-w-md rounded-full bg-slate-200 overflow-hidden">
                <div
                  className="h-full rounded-full bg-indigo-600 transition-all duration-300"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.round(
                        (subscription.cases_used_this_period /
                          Math.max(1, subscription.monthly_case_limit)) *
                          100
                      )
                    )}%`,
                  }}
                />
              </div>
              <span className="text-xs font-semibold text-slate-700 whitespace-nowrap">
                {subscription.cases_used_this_period} / {subscription.monthly_case_limit} cases used
              </span>
            </div>
          </div>
          <div>
            {subscription.plan_key === "agency_sandbox" ? (
              <button
                type="button"
                onClick={handleUpgradePro}
                disabled={upgrading}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-indigo-700 transition-colors"
              >
                {upgrading ? "Loading..." : "Upgrade to Agency Pro (€149/mo)"}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleManageBilling}
                disabled={upgrading}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs hover:bg-slate-50 transition-colors"
              >
                Manage Billing & Invoices
              </button>
            )}
          </div>
        </div>
      )}

      {/* Metric Cards */}
      <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-2xs">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            {t("totalCases")}
          </div>
          <div className="mt-2 text-3xl font-extrabold text-slate-900">{stats.total}</div>
        </div>
        <div className="rounded-2xl border border-blue-100 bg-blue-50/40 p-5 shadow-2xs">
          <div className="text-xs font-semibold text-blue-600 uppercase tracking-wider">
            {t("inProgress")}
          </div>
          <div className="mt-2 text-3xl font-extrabold text-blue-900">{stats.inProgress}</div>
        </div>
        <div className="rounded-2xl border border-purple-100 bg-purple-50/40 p-5 shadow-2xs">
          <div className="text-xs font-semibold text-purple-600 uppercase tracking-wider">
            {t("awaitingReview")}
          </div>
          <div className="mt-2 text-3xl font-extrabold text-purple-900">{stats.awaitingReview}</div>
        </div>
        <div className="rounded-2xl border border-emerald-100 bg-emerald-50/40 p-5 shadow-2xs">
          <div className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">
            {t("completed")}
          </div>
          <div className="mt-2 text-3xl font-extrabold text-emerald-900">{stats.completed}</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <div className="pointer-events-none absolute inset-y-0 start-0 flex items-center ps-3 text-slate-400">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="w-full rounded-xl border border-slate-200 bg-white py-2 ps-9 pe-3 text-xs text-slate-900 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/15"
          />
        </div>

        <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
          {[
            { id: "all", label: t("filterAll") },
            { id: "invited", label: t("filterInvited") },
            { id: "in_progress", label: t("filterInProgress") },
            { id: "awaiting_review", label: t("filterReview") },
            { id: "completed", label: t("filterCompleted") },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                statusFilter === tab.id
                  ? "bg-slate-900 text-white shadow-2xs"
                  : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Cases Table */}
      <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xs">
        {filteredCases.length === 0 ? (
          <div className="p-12 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="mt-3 text-sm font-bold text-slate-900">{t("emptyCases")}</h3>
            <p className="mt-1 text-xs text-slate-500">{t("emptyCasesSub")}</p>
            <div className="mt-5">
              <button
                type="button"
                onClick={() => setIsNewCaseOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-indigo-700 transition-colors"
              >
                {t("newCase")}
              </button>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-start text-xs">
              <thead className="border-b border-slate-200 bg-slate-50/70 text-slate-500 uppercase tracking-wider font-semibold">
                <tr>
                  <th scope="col" className="px-5 py-3.5 text-start">{t("candidate")}</th>
                  <th scope="col" className="px-5 py-3.5 text-start">{t("template")}</th>
                  <th scope="col" className="px-5 py-3.5 text-start">{t("status")}</th>
                  <th scope="col" className="px-5 py-3.5 text-start">{t("progress")}</th>
                  <th scope="col" className="px-5 py-3.5 text-start">{t("created")}</th>
                  <th scope="col" className="px-5 py-3.5 text-end">{t("actions")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredCases.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-5 py-4 whitespace-nowrap">
                      <div className="font-semibold text-slate-900">{c.candidate_name}</div>
                      <div className="text-[11px] text-slate-500 font-mono">{c.candidate_email}</div>
                    </td>
                    <td className="px-5 py-4">
                      <div className="font-medium text-slate-900 line-clamp-1 max-w-xs">
                        {c.form_title || "Official Administrative Template"}
                      </div>
                      {c.notes && (
                        <div className="text-[10px] text-slate-400 italic line-clamp-1">
                          {c.notes}
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap">
                      {getStatusBadge(c.status)}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-slate-100 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              c.progress_percent === 100 ? "bg-emerald-500" : "bg-indigo-600"
                            }`}
                            style={{ width: `${c.progress_percent}%` }}
                          />
                        </div>
                        <span className="font-mono text-[11px] font-semibold text-slate-700">
                          {c.progress_percent}%
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-slate-500">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-4 whitespace-nowrap text-end">
                      <div className="inline-flex items-center gap-2 justify-end">
                        {c.invite_token && (
                          <button
                            type="button"
                            onClick={() => handleCopyLink(c)}
                            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                          >
                            {copiedCaseId === c.id ? (
                              <span className="text-emerald-600 font-bold">{t("copied")}</span>
                            ) : (
                              <span>{t("copyInvite")}</span>
                            )}
                          </button>
                        )}
                        {c.session_public_id && (
                          <Link
                            href={`/application/session/${c.session_public_id}`}
                            className="inline-flex items-center gap-1 rounded-lg bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors"
                          >
                            {t("reviewInStudio")}
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

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
    </div>
  );
}
