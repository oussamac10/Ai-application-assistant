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
    <div className="min-h-screen bg-[#0A0E17] text-slate-100 pb-20">
      {/* Hero Header */}
      <section className="bg-[#0F1522] border-b border-white/10">
        <div className="max-w-6xl mx-auto px-4 py-12 sm:py-16 text-center">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold mb-4">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Verified Official Public Authorities</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
            Official Municipal & Government Portals
          </h1>
          <p className="mt-3 text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Find your local city administration, municipal office, or immigration authority. Understand questions and complete official administrative forms in your native language — completely free of charge.
          </p>

          {/* Search Box in Hero */}
          <div className="mt-8 max-w-xl mx-auto relative">
            <Search className="pointer-events-none absolute left-4 top-3.5 w-5 h-5 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by city, municipality, authority name, or postal code..."
              className="w-full rounded-2xl border border-white/10 bg-[#0A0E17] py-3 pl-12 pr-4 text-sm text-slate-100 placeholder-slate-500 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>
        </div>
      </section>

      {/* Directory Main */}
      <main className="max-w-6xl mx-auto px-4 pt-10">
        {/* Filters and Counters */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-8">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
              Authorities Directory
            </span>
            <span className="rounded-full bg-[#151D2E] border border-white/10 text-slate-200 px-2.5 py-0.5 text-xs font-bold">
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
                className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                  typeFilter === tab.id
                    ? "bg-emerald-500 text-slate-950 font-bold shadow-2xs"
                    : "bg-[#0F1522] text-slate-300 hover:bg-[#151D2E] hover:text-white border border-white/10"
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
              <div key={i} className="h-56 rounded-2xl bg-[#0F1522] border border-white/10 animate-pulse" />
            ))}
          </div>
        ) : filteredOrgs.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-[#0F1522] p-12 text-center shadow-2xs">
            <Building2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <h3 className="text-base font-bold text-white">No Authorities Found</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
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
                  className="rounded-2xl border border-white/10 bg-[#0F1522] p-6 shadow-2xs hover:shadow-md hover:border-emerald-500/40 transition-all flex flex-col justify-between"
                >
                  <div>
                    {/* Header: Crest + Name */}
                    <div className="flex items-start gap-3.5 mb-4">
                      <div
                        className={`w-12 h-12 rounded-xl border flex items-center justify-center shrink-0 overflow-hidden ${
                          logoUrl
                            ? "bg-white border-white/20 p-1"
                            : "bg-[#151D2E] border-white/10 p-2"
                        }`}
                      >
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
                          <h3 className="text-sm font-bold text-white leading-snug line-clamp-1">
                            {org.name}
                          </h3>
                        </div>
                        {org.is_verified_government && (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400 mt-0.5">
                            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                            Official Government Authority
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Address & Info */}
                    {org.office_address && (
                      <p className="text-xs text-slate-400 flex items-start gap-1.5 mb-3 line-clamp-2">
                        <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
                        <span>{org.office_address}</span>
                      </p>
                    )}

                    {org.description && (
                      <p className="text-xs text-slate-400 line-clamp-2 mb-4">
                        {org.description}
                      </p>
                    )}

                    {/* Published forms counter */}
                    <div className="flex items-center gap-2 mb-4">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
                        <FileText className="w-3.5 h-3.5" />
                        <span>{org.published_forms_count} Official Form{org.published_forms_count === 1 ? "" : "s"}</span>
                      </span>

                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Free
                      </span>
                    </div>
                  </div>

                  {/* Open Portal Link */}
                  <div className="pt-4 border-t border-white/[0.08]">
                    <Link
                      href={`/organizations/${org.slug}`}
                      className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold transition-colors"
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
