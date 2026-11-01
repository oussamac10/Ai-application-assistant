"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/features/auth/context/AuthProvider";
import {
  ShieldAlert,
  Building2,
  Users,
  FileSpreadsheet,
  Cpu,
  Flame,
  CheckCircle2,
  ExternalLink,
  RefreshCw,
  Lock,
} from "lucide-react";

interface AdminKPIs {
  total_organizations: number;
  total_users: number;
  total_cases: number;
  total_ai_events: number;
  total_tokens: number;
  total_cost_eur: number;
}

interface AdminFirewall {
  max_session_cost_eur: number;
  ai_provider: string;
  translation_provider: string;
  field_detection_provider: string;
}

interface AdminOrg {
  id: string;
  name: string;
  slug: string;
  created_at: string | null;
  member_count: number;
  case_count: number;
  plan_key: string;
  monthly_case_limit: number;
  status: string;
}

interface AdminOverviewData {
  kpis: AdminKPIs;
  firewall: AdminFirewall;
  organizations: AdminOrg[];
}

export default function AdminPage() {
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState<AdminOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/overview", {
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });
      if (res.status === 401 || res.status === 403) {
        setError("forbidden");
        setLoading(false);
        return;
      }
      if (!res.ok) {
        throw new Error("Failed to load admin overview");
      }
      const json = await res.json();
      setData(json);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error fetching admin data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading) {
      fetchOverview();
    }
  }, [authLoading, user]);

  if (authLoading || (loading && !error)) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center p-4">
        <div className="w-10 h-10 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Connecting to Admin Tower...
        </p>
      </div>
    );
  }

  // Not platform admin or unauthenticated
  if (error === "forbidden" || !user || user.role !== "platform_admin") {
    return (
      <div className="min-h-[75vh] flex items-center justify-center px-4 py-12">
        <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200 p-8 shadow-sm text-center space-y-6">
          <div className="w-14 h-14 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto text-amber-600">
            <Lock className="w-7 h-7" />
          </div>
          <div className="space-y-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Platform Admin Restricted
            </h1>
            <p className="text-xs text-slate-600 leading-relaxed">
              This console is reserved for platform administrators and system operators.
              Please sign in with authorized admin credentials.
            </p>
          </div>

          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 text-start space-y-1">
            <p className="font-semibold text-slate-900">Developer Note:</p>
            <p className="text-slate-500">
              In development, accounts with email <code className="bg-white px-1.5 py-0.5 rounded border border-slate-200 font-mono text-indigo-700">admin@example.com</code> are granted platform admin privileges automatically.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <Link
              href="/login?redirect=/admin"
              className="btn-primary flex-1 py-2.5 text-xs font-semibold justify-center"
            >
              Sign In to Admin
            </Link>
            <Link
              href="/portal"
              className="btn-secondary flex-1 py-2.5 text-xs font-semibold justify-center"
            >
              Go to Agency Portal
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50/60 pb-16 pt-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="p-2 rounded-xl bg-indigo-600 text-white shadow-xs">
                <Flame className="w-5 h-5" />
              </span>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                Founder Admin Control Tower
              </h1>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Live Engine
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Global multi-tenant governance, live AI cost firewall, and tenant roster.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={fetchOverview}
              className="btn-secondary py-2 px-3 text-xs font-medium inline-flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <Link
              href="/portal"
              className="btn-secondary py-2 px-3 text-xs font-medium inline-flex items-center gap-1.5"
            >
              Agency Studio
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
            <Link
              href="/pricing"
              className="btn-primary py-2 px-3 text-xs font-medium inline-flex items-center gap-1.5"
            >
              Commercial Plans
            </Link>
          </div>
        </div>

        {/* Global KPIs */}
        {data && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-semibold uppercase tracking-wider">Organizations</span>
                  <Building2 className="w-4 h-4 text-indigo-600" />
                </div>
                <div className="text-2xl font-extrabold text-slate-900 tabular-nums">
                  {data.kpis.total_organizations}
                </div>
                <p className="text-[11px] text-slate-500">Active relocation agencies & authorities</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-semibold uppercase tracking-wider">Total Intake Cases</span>
                  <FileSpreadsheet className="w-4 h-4 text-indigo-600" />
                </div>
                <div className="text-2xl font-extrabold text-slate-900 tabular-nums">
                  {data.kpis.total_cases}
                </div>
                <p className="text-[11px] text-slate-500">Across worldwide immigration & visa flows</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-semibold uppercase tracking-wider">Registered Staff</span>
                  <Users className="w-4 h-4 text-indigo-600" />
                </div>
                <div className="text-2xl font-extrabold text-slate-900 tabular-nums">
                  {data.kpis.total_users}
                </div>
                <p className="text-[11px] text-slate-500">Case managers & platform operators</p>
              </div>

              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-semibold uppercase tracking-wider">AI Burn (EUR)</span>
                  <Cpu className="w-4 h-4 text-indigo-600" />
                </div>
                <div className="text-2xl font-extrabold text-slate-900 tabular-nums text-emerald-600">
                  €{data.kpis.total_cost_eur.toFixed(4)}
                </div>
                <p className="text-[11px] text-slate-500">
                  {data.kpis.total_tokens.toLocaleString()} tokens across {data.kpis.total_ai_events} calls
                </p>
              </div>
            </div>

            {/* AI Cost Firewall & Reliability Guard */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-indigo-600" />
                  <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                    AI Spend Circuit Breaker & Pipeline Health
                  </h2>
                </div>
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Hard Limit: €0.25 / Session
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs pt-1">
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-500 block mb-1">Reasoning Provider</span>
                  <span className="font-semibold text-slate-800 font-mono">{data.firewall.ai_provider}</span>
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-500 block mb-1">Translation Engine</span>
                  <span className="font-semibold text-slate-800 font-mono">{data.firewall.translation_provider}</span>
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-500 block mb-1">Field Detection</span>
                  <span className="font-semibold text-slate-800 font-mono">{data.firewall.field_detection_provider}</span>
                </div>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-500 block mb-1">Budget Breaker</span>
                  <span className="font-semibold text-emerald-700">Enforced Fail-Safe</span>
                </div>
              </div>
            </div>

            {/* Organizations Directory */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="p-5 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-slate-900">Tenant Organizations</h2>
                  <p className="text-xs text-slate-500">Live roster of subscribed agencies and municipal authorities.</p>
                </div>
                <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg">
                  {data.organizations.length} Tenancies
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-start text-xs">
                  <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4 text-start">Organization</th>
                      <th className="py-3 px-4 text-start">Plan</th>
                      <th className="py-3 px-4 text-start">Monthly Quota</th>
                      <th className="py-3 px-4 text-start">Cases</th>
                      <th className="py-3 px-4 text-start">Staff</th>
                      <th className="py-3 px-4 text-start">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.organizations.map((org) => (
                      <tr key={org.id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="py-3.5 px-4 font-semibold text-slate-900">
                          {org.name}
                          <span className="block text-[11px] font-mono text-slate-400 font-normal">
                            /{org.slug}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-medium text-slate-700 capitalize">
                          {org.plan_key.replace("_", " ")}
                        </td>
                        <td className="py-3.5 px-4 text-slate-600 tabular-nums">
                          {org.monthly_case_limit} cases/mo
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-slate-900 tabular-nums">
                          {org.case_count}
                        </td>
                        <td className="py-3.5 px-4 text-slate-600 tabular-nums">
                          {org.member_count}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 capitalize">
                            {org.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {data.organizations.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-slate-400">
                          No organizations registered yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
