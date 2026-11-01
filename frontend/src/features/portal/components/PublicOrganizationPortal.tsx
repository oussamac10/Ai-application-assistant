/* eslint-disable @next/next/no-img-element */
"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ShieldCheck,
  Building2,
  MapPin,
  Globe,
  Mail,
  Search,
  FileText,
  CheckCircle2,
  ArrowRight,
  Loader2,
  ExternalLink,
  Layers,
  Sparkles,
  Info,
} from "lucide-react";
import { getPublicOrganizationBySlug } from "../services/portalClient";
import { PublicOrganizationDetail, PublicPublishedFormItem } from "../types";
import { createSession, ApiError } from "@/features/form-session/services/apiClient";
import { setSessionToken } from "@/features/form-session/services/sessionCredentials";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";

interface PublicOrganizationPortalProps {
  slug: string;
}

export function PublicOrganizationPortal({ slug }: PublicOrganizationPortalProps) {
  const router = useRouter();
  const { setLocale } = useLanguage();

  const [org, setOrg] = useState<PublicOrganizationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [citizenLanguage, setCitizenLanguage] = useState("en");

  // Starting session state
  const [startingFormId, setStartingFormId] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getPublicOrganizationBySlug(slug)
      .then((data) => {
        setOrg(data);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Public portal could not be loaded.");
      })
      .finally(() => setLoading(false));
  }, [slug]);

  const filteredForms = useMemo(() => {
    if (!org) return [];
    return org.published_forms.filter((f) => {
      if (searchQuery.trim().length > 0) {
        const q = searchQuery.toLowerCase();
        const matchesName = f.name.toLowerCase().includes(q);
        const matchesDesc = (f.description || "").toLowerCase().includes(q);
        const matchesKey = f.key.toLowerCase().includes(q);
        return matchesName || matchesDesc || matchesKey;
      }
      return true;
    });
  }, [org, searchQuery]);

  const handleStartForm = async (form: PublicPublishedFormItem) => {
    try {
      setStartingFormId(form.id);
      setStartError(null);

      // Determine output language (destination language of the form)
      const outputLang =
        form.supported_output_languages?.[0] || form.source_language || "de";

      // Set user language in context
      setLocale(citizenLanguage);

      // Call API to initialize an anonymous free session for this form version
      const session = await createSession(
        form.active_version_id,
        citizenLanguage,
        outputLang
      );

      // Store ownership token
      if (session.ownershipToken) {
        setSessionToken(session.publicId, session.ownershipToken);
        try {
          sessionStorage.setItem(`session_token_${session.publicId}`, session.ownershipToken);
        } catch {
          // Non-browser fallback
        }
      }

      // Navigate directly into the guided question intake
      router.push(`/application/session/${session.publicId}`);
    } catch (err: unknown) {
      let msg = "Failed to start form session";
      if (err instanceof ApiError && err.detail) {
        msg = err.detail;
      } else if (err instanceof Error) {
        msg =
          err.message === "unknown"
            ? "Failed to start form session. Please try again."
            : err.message;
      }
      setStartError(msg);
      setStartingFormId(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
        <p className="text-sm font-medium text-slate-600">
          Loading verified authority portal...
        </p>
      </div>
    );
  }

  if (error || !org) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center max-w-lg mx-auto">
        <div className="w-14 h-14 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mb-4">
          <Building2 className="w-7 h-7" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">Portal Not Found</h2>
        <p className="text-sm text-slate-500 mt-2 mb-6">
          {error || `The requested public portal "${slug}" does not exist or has no active forms.`}
        </p>
        <Link
          href="/organizations"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 text-white font-medium text-sm shadow-sm hover:bg-blue-700 transition-colors"
        >
          <Search className="w-4 h-4" /> Browse Authority Directory
        </Link>
      </div>
    );
  }

  const logoUrl = org.has_logo ? `/api/public/organizations/${org.slug}/logo` : null;

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Official Government Authority Header Banner */}
      <section className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 py-8 sm:py-10">
          {/* Top Breadcrumb & Citizen Free Notice */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
            <Link
              href="/organizations"
              className="text-xs font-semibold text-slate-500 hover:text-blue-600 flex items-center gap-1.5 transition-colors"
            >
              <span>← All Municipal Authorities & Portals</span>
            </Link>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-bold">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>100% Free for Citizens & Applicants</span>
            </div>
          </div>

          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="flex items-start sm:items-center gap-4">
              {/* Crest / Logo */}
              <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center justify-center p-2.5 overflow-hidden shrink-0">
                {logoUrl ? (
                  <img
                    src={logoUrl}
                    alt={`${org.name} Official Logo`}
                    className="max-w-full max-h-full object-contain"
                  />
                ) : (
                  <Building2 className="w-9 h-9 text-slate-400" />
                )}
              </div>

              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                    {org.name}
                  </h1>
                  {org.is_verified_government && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 text-emerald-800 px-2.5 py-0.5 text-xs font-bold border border-emerald-200">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                      Verified Official Authority
                    </span>
                  )}
                </div>

                <div className="mt-2 flex flex-wrap items-center gap-y-1.5 gap-x-4 text-xs text-slate-500">
                  {org.office_address && (
                    <div className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-slate-400" />
                      <span>{org.office_address}</span>
                    </div>
                  )}
                  {org.official_website_url && (
                    <a
                      href={org.official_website_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-blue-600 hover:text-blue-800 font-medium"
                    >
                      <Globe className="w-3.5 h-3.5" />
                      <span>Official Website</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                  {org.contact_email && (
                    <div className="flex items-center gap-1">
                      <Mail className="w-3.5 h-3.5 text-slate-400" />
                      <span>{org.contact_email}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Language Selection Card for Citizen */}
            <div className="w-full md:w-auto bg-slate-50 border border-slate-200 rounded-2xl p-4 shrink-0">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                Translate Questions Into:
              </label>
              <div className="flex flex-wrap gap-1.5 max-w-xs">
                {UNIVERSAL_LANGUAGES.slice(0, 8).map((lang) => (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => {
                      setCitizenLanguage(lang.code);
                      setLocale(lang.code);
                    }}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                      citizenLanguage === lang.code
                        ? "bg-blue-600 text-white shadow-xs"
                        : "bg-white text-slate-700 hover:bg-slate-200 border border-slate-200"
                    }`}
                  >
                    <span className="font-mono text-[10px] uppercase opacity-75">{lang.code}</span>
                    <span>{lang.nativeName}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {org.description && (
            <p className="mt-6 text-sm text-slate-600 max-w-3xl leading-relaxed border-t border-slate-100 pt-4">
              {org.description}
            </p>
          )}
        </div>
      </section>

      {/* Main Content Area: Published Forms Catalog */}
      <main className="max-w-6xl mx-auto px-4 pt-8">
        {startError && (
          <div className="mb-6 p-4 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-center justify-between">
            <span>{startError}</span>
            <button
              onClick={() => setStartError(null)}
              className="text-red-500 font-bold ml-4"
            >
              ✕
            </button>
          </div>
        )}

        {/* Guidance Banner */}
        <div className="mb-8 rounded-2xl border border-blue-100 bg-linear-to-r from-blue-50/70 via-indigo-50/30 to-white p-5 flex items-start gap-3.5 shadow-2xs">
          <Sparkles className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
          <div className="text-xs text-slate-700 space-y-1">
            <span className="font-bold text-slate-900">
              Multilingual Assistance for Official Administrative Forms:
            </span>
            <p className="text-slate-600">
              Select the administrative form you need below. The assistant will guide you step-by-step in your chosen language, normalize dates, addresses, and family statuses, and generate an official ready-to-sign PDF adhering to German administrative standards.
            </p>
          </div>
        </div>

        {/* Search & Category Filter */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
          <div className="relative w-full sm:w-80">
            <Search className="pointer-events-none absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search forms, permits, or topics..."
              className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-3 text-xs text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/15"
            />
          </div>
        </div>

        {/* Forms Catalog Grid */}
        {filteredForms.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-2xs">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-bold text-slate-800">No Forms Found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              No published forms match your current search query. Try searching for a different keyword.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {filteredForms.map((form) => {
              const isStarting = startingFormId === form.id;

              return (
                <div
                  key={form.id}
                  className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-2xs hover:shadow-md hover:border-blue-300 transition-all flex flex-col justify-between"
                >
                  <div>
                    {/* Tags row */}
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-100">
                        Official Form
                      </span>
                      <span className="text-[11px] font-mono text-slate-400">
                        {form.fields_count} Questions
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-slate-900 tracking-tight">
                      {form.name}
                    </h3>

                    {form.instructions && (
                      <p className="mt-2 text-xs text-slate-500 line-clamp-2">
                        {form.instructions}
                      </p>
                    )}

                    {/* Required Documents Checklist Preview */}
                    {form.required_documents && form.required_documents.length > 0 && (
                      <div className="mt-4 pt-3.5 border-t border-slate-100">
                        <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5 mb-2">
                          <Info className="w-3.5 h-3.5 text-blue-600" />
                          Required Supporting Documents:
                        </span>
                        <ul className="space-y-1">
                          {form.required_documents.slice(0, 3).map((doc, idx) => (
                            <li
                              key={idx}
                              className="text-xs text-slate-600 flex items-start gap-2"
                            >
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0 mt-1.5" />
                              <span className="line-clamp-1">{doc}</span>
                            </li>
                          ))}
                          {form.required_documents.length > 3 && (
                            <li className="text-[11px] text-slate-400 pl-3.5">
                              + {form.required_documents.length - 3} more items
                            </li>
                          )}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Action Button */}
                  <div className="mt-6 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                    <span className="text-[11px] text-emerald-700 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Free Citizen Intake
                    </span>

                    <div className="flex flex-wrap items-center gap-2">
                      {/* Language Selector on Form Card */}
                      <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs">
                        <Globe className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                        <select
                          value={citizenLanguage}
                          onChange={(e) => {
                            setCitizenLanguage(e.target.value);
                            setLocale(e.target.value);
                          }}
                          className="bg-transparent text-xs font-semibold text-slate-700 focus:outline-none cursor-pointer pr-1"
                          aria-label="Select assistance language"
                        >
                          {UNIVERSAL_LANGUAGES.map((lang) => (
                            <option key={lang.code} value={lang.code}>
                              {lang.nativeName} ({lang.code.toUpperCase()})
                            </option>
                          ))}
                        </select>
                      </div>

                      <button
                        type="button"
                        disabled={isStarting}
                        onClick={() => handleStartForm(form)}
                        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-[0.98] text-white text-xs font-bold shadow-xs transition-all disabled:opacity-50 cursor-pointer"
                      >
                        {isStarting ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            <span>Preparing Questions...</span>
                          </>
                        ) : (
                          <>
                            <span>
                              Start in{" "}
                              {UNIVERSAL_LANGUAGES.find((l) => l.code === citizenLanguage)?.nativeName ||
                                citizenLanguage.toUpperCase()}
                            </span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </>
                        )}
                      </button>
                    </div>
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
