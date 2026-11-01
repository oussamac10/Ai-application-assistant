/* eslint-disable @next/next/no-img-element */
"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Building2,
  ShieldCheck,
  MapPin,
  Search,
  ArrowRight,
  Loader2,
  FileText,
  CheckCircle2,
  Sparkles,
} from "lucide-react";
import { listPublicOrganizations } from "../services/portalClient";
import { PublicOrganizationSummary } from "../types";

export function CitizenDirectory() {
  const [organizations, setOrganizations] = useState<PublicOrganizationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  useEffect(() => {
    setLoading(true);
    listPublicOrganizations()
      .then((data) => {
        setOrganizations(data);
      })
      .catch((err) => {
        console.error("Failed to load organizations:", err);
      })
      .finally(() => setLoading(false));
  }, []);

  const filteredOrgs = useMemo(() => {
    return organizations.filter((org) => {
      if (typeFilter !== "all" && org.organization_type !== typeFilter) {
        return false;
      }
      if (searchQuery.trim().length > 0) {
        const q = searchQuery.toLowerCase();
        const matchesName = org.name.toLowerCase().includes(q);
        const matchesAddress = (org.office_address || "").toLowerCase().includes(q);
        const matchesSlug = org.slug.toLowerCase().includes(q);
        return matchesName || matchesAddress || matchesSlug;
      }
      return true;
    });
  }, [organizations, typeFilter, searchQuery]);

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Hero Header */}
      <section className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 py-12 sm:py-16 text-center">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-bold mb-4">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
            <span>Verified Official Public Authorities</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            Official Municipal & Government Portals
          </h1>
          <p className="mt-3 text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Find your local city administration, Bürgeramt, or immigration authority. Understand questions and complete official administrative forms in your native language — completely free of charge.
          </p>

          {/* Search Box in Hero */}
          <div className="mt-8 max-w-xl mx-auto relative">
            <Search className="pointer-events-none absolute left-4 top-3.5 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by city, municipality, authority name, or postal code..."
              className="w-full rounded-2xl border border-slate-300 bg-white py-3 pl-12 pr-4 text-sm text-slate-900 shadow-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/15"
            />
          </div>
        </div>
      </section>

      {/* Directory Main */}
      <main className="max-w-6xl mx-auto px-4 pt-10">
        {/* Filters and Counters */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-8">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Authorities Directory
            </span>
            <span className="rounded-full bg-slate-200 text-slate-700 px-2.5 py-0.5 text-xs font-bold">
              {filteredOrgs.length}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: "all", label: "All Authorities" },
              { id: "government", label: "Municipalities & Cities" },
              { id: "business", label: "Specialized Agencies" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setTypeFilter(tab.id)}
                className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold transition-all ${
                  typeFilter === tab.id
                    ? "bg-slate-900 text-white shadow-2xs"
                    : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Loading State */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-56 rounded-2xl bg-slate-200/60 animate-pulse" />
            ))}
          </div>
        ) : filteredOrgs.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-2xs">
            <Building2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-bold text-slate-800">No Authorities Found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              We couldn’t find an authority matching your search query. Try clearing your filters or searching by a broader city name.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredOrgs.map((org) => {
              const logoUrl = org.has_logo
                ? `/api/public/organizations/${org.slug}/logo`
                : null;

              return (
                <div
                  key={org.id}
                  className="rounded-2xl border border-slate-200 bg-white p-6 shadow-2xs hover:shadow-md hover:border-blue-300 transition-all flex flex-col justify-between"
                >
                  <div>
                    {/* Header: Crest + Name */}
                    <div className="flex items-start gap-3.5 mb-4">
                      <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center p-2 shrink-0 overflow-hidden">
                        {logoUrl ? (
                          <img
                            src={logoUrl}
                            alt={org.name}
                            className="max-w-full max-h-full object-contain"
                          />
                        ) : (
                          <Building2 className="w-6 h-6 text-slate-400" />
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <h3 className="text-sm font-bold text-slate-900 leading-snug line-clamp-1">
                            {org.name}
                          </h3>
                        </div>
                        {org.is_verified_government && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 mt-0.5">
                            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                            Official Government Authority
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Address & Info */}
                    {org.office_address && (
                      <p className="text-xs text-slate-500 flex items-start gap-1.5 mb-3 line-clamp-2">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                        <span>{org.office_address}</span>
                      </p>
                    )}

                    {org.description && (
                      <p className="text-xs text-slate-600 line-clamp-2 mb-4">
                        {org.description}
                      </p>
                    )}

                    {/* Published forms counter */}
                    <div className="flex items-center gap-2 mb-4">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 text-xs font-semibold">
                        <FileText className="w-3.5 h-3.5" />
                        <span>{org.published_forms_count} Official Form{org.published_forms_count === 1 ? "" : "s"}</span>
                      </span>

                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-emerald-50 text-emerald-700 text-xs font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Free
                      </span>
                    </div>
                  </div>

                  {/* Open Portal Link */}
                  <div className="pt-4 border-t border-slate-100">
                    <Link
                      href={`/organizations/${org.slug}`}
                      className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-blue-600 text-white text-xs font-semibold transition-colors"
                    >
                      <span>Open Official Portal</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
