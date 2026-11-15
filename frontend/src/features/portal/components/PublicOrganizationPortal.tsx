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
  QrCode,
  X,
} from "lucide-react";
import { ShareFormModal } from "./ShareFormModal";
import { CategoryIcon } from "./CategoryIcon";
import {
  getPublicOrganizationBySlug,
  semanticSearchOrganizationForms,
} from "../services/portalClient";
import {
  PublicOrganizationDetail,
  PublicPublishedFormItem,
  PublicCategoryItem,
  FormSemanticSearchResult,
} from "../types";
import { createSession, ApiError } from "@/features/form-session/services/apiClient";
import { setSessionToken } from "@/features/form-session/services/sessionCredentials";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import { ModernSelect } from "@/components/ui/ModernSelect";
import {
  applyBrandThemeToDocument,
  hydratePersistedBrandTheme,
} from "../utils/theme";

interface PublicOrganizationPortalProps {
  slug: string;
}

export interface EnhancedFormItem extends PublicPublishedFormItem {
  semantic_match?: FormSemanticSearchResult;
}

export function PublicOrganizationPortal({ slug }: PublicOrganizationPortalProps) {
  const router = useRouter();
  const { locale, setLocale } = useLanguage();

  const [org, setOrg] = useState<PublicOrganizationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategorySlug, setSelectedCategorySlug] = useState<string>("all");
  const [citizenLanguage, setCitizenLanguage] = useState(locale || "en");

  // Semantic search states (Phase G5-AI)
  const [semanticResults, setSemanticResults] = useState<FormSemanticSearchResult[] | null>(null);
  const [isSearchingSemantically, setIsSearchingSemantically] = useState(false);

  // Keep citizenLanguage in sync with active UI locale
  useEffect(() => {
    if (locale) {
      setCitizenLanguage(locale);
    }
  }, [locale]);

  // Debounced semantic search across multilingual municipal forms
  useEffect(() => {
    const trimmed = searchQuery.trim();
    if (trimmed.length < 2) {
      setSemanticResults(null);
      setIsSearchingSemantically(false);
      return;
    }

    setIsSearchingSemantically(true);
    const timer = setTimeout(async () => {
      try {
        const results = await semanticSearchOrganizationForms(slug, trimmed);
        setSemanticResults(results);
      } catch (err) {
        console.error("Semantic search failed:", err);
        setSemanticResults(null);
      } finally {
        setIsSearchingSemantically(false);
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [searchQuery, slug]);

  // Starting session state
  const [startingFormId, setStartingFormId] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [sharingForm, setSharingForm] = useState<PublicPublishedFormItem | null>(null);

  const ALL_FORMS_LABELS: Record<string, string> = {
    de: "Alle Formulare",
    en: "All Forms",
    ar: "جميع النماذج",
    fr: "Tous les formulaires",
    tr: "Tüm Formlar",
    uk: "Всі форми",
    es: "Todos los formularios",
    ru: "Все формы",
    it: "Tutti i moduli",
    pl: "Wszystkie formularze",
  };

  const getCategoryLabel = (cat: PublicCategoryItem): string => {
    const lang = citizenLanguage;
    if (cat.translations && cat.translations[lang]?.name) {
      return cat.translations[lang].name;
    }
    if (cat.translations?.en?.name) {
      return cat.translations.en.name;
    }
    if (cat.translations?.de?.name) {
      return cat.translations.de.name;
    }
    return cat.name;
  };

  useEffect(() => {
    setLoading(true);
    setError(null);
    getPublicOrganizationBySlug(slug)
      .then((data) => {
        setOrg(data);
        applyBrandThemeToDocument(data.ui_theme_config, { persist: false });
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Public portal could not be loaded.");
      })
      .finally(() => setLoading(false));
    return () => {
      hydratePersistedBrandTheme();
    };
  }, [slug]);

  const filteredForms = useMemo<EnhancedFormItem[]>(() => {
    if (!org) return [];

    const semanticMap = new Map<string, FormSemanticSearchResult>();
    if (semanticResults && semanticResults.length > 0) {
      for (const res of semanticResults) {
        semanticMap.set(res.template_id, res);
        semanticMap.set(res.key, res);
      }
    }

    const items: EnhancedFormItem[] = [];

    for (const f of org.published_forms) {
      // 1. Category Filter
      if (selectedCategorySlug !== "all") {
        const matchesId =
          f.category_id &&
          org.categories?.some(
            (c) => c.slug === selectedCategorySlug && c.id === f.category_id
          );
        const matchesSlug =
          f.category_slug === selectedCategorySlug ||
          (f.category && f.category.toLowerCase() === selectedCategorySlug.toLowerCase());
        if (!matchesId && !matchesSlug) {
          continue;
        }
      }

      // 2. Search Query Filter
      if (searchQuery.trim().length > 0) {
        const sem = semanticMap.get(f.id) || semanticMap.get(f.key);
        const q = searchQuery.toLowerCase();
        const matchesName = f.name.toLowerCase().includes(q);
        const matchesDesc = (f.description || "").toLowerCase().includes(q);
        const matchesKey = f.key.toLowerCase().includes(q);

        if (sem) {
          items.push({ ...f, semantic_match: sem });
        } else if (matchesName || matchesDesc || matchesKey) {
          items.push(f);
        }
      } else {
        items.push(f);
      }
    }

    // Sort items: semantic matches first (by relevance_score desc)
    if (searchQuery.trim().length > 0) {
      items.sort((a, b) => {
        const scoreA = a.semantic_match ? a.semantic_match.relevance_score : 0;
        const scoreB = b.semantic_match ? b.semantic_match.relevance_score : 0;
        return scoreB - scoreA;
      });
    }

    return items;
  }, [org, selectedCategorySlug, searchQuery, semanticResults]);

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
      let msg = "Failed to start form session. Please try again.";
      if (err instanceof ApiError && err.detail && err.detail !== "unknown") {
        msg = err.detail;
      } else if (err instanceof Error && err.message && err.message !== "unknown") {
        msg = err.message;
      }
      setStartError(msg);
      setStartingFormId(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] bg-[#0A0E17] text-slate-100 flex flex-col items-center justify-center space-y-4">
        <Loader2 className="w-10 h-10 text-emerald-400 animate-spin" />
        <p className="text-sm font-medium text-slate-400">
          Loading verified authority portal...
        </p>
      </div>
    );
  }

  if (error || !org) {
    return (
      <div className="min-h-[70vh] bg-[#0A0E17] text-slate-100 flex flex-col items-center justify-center p-6 text-center">
        <div className="max-w-lg mx-auto flex flex-col items-center">
          <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center justify-center mb-4">
            <Building2 className="w-7 h-7" />
          </div>
          <h2 className="text-xl font-bold text-white">Portal Not Found</h2>
          <p className="text-sm text-slate-400 mt-2 mb-6">
            {error || `The requested public portal "${slug}" does not exist or has no active forms.`}
          </p>
          <Link
            href="/organizations"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-500 text-slate-950 font-bold text-sm shadow-sm hover:bg-emerald-400 transition-colors"
          >
            <Search className="w-4 h-4" /> Browse Authority Directory
          </Link>
        </div>
      </div>
    );
  }

  const logoUrl = org.has_logo ? `/api/public/organizations/${org.slug}/logo` : null;

  return (
    <div className="min-h-screen bg-[#0A0E17] text-slate-100 pb-20">
      {/* Official Government Authority Header Banner */}
      <section className="bg-[#0F1522] border-b border-white/10">
        <div className="max-w-6xl mx-auto px-4 py-8 sm:py-10">
          {/* Top Breadcrumb & Citizen Free Notice */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
            <Link
              href="/organizations"
              className="text-xs font-semibold text-slate-400 hover:text-emerald-400 flex items-center gap-1.5 transition-colors"
            >
              <span>← All Municipal Authorities & Portals</span>
            </Link>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>100% Free for Citizens & Applicants</span>
            </div>
          </div>

          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="flex items-start sm:items-center gap-4">
              {/* Crest / Logo */}
              <div
                className={`w-16 h-16 sm:w-20 sm:h-20 rounded-2xl border shadow-xs flex items-center justify-center overflow-hidden shrink-0 ${
                  logoUrl
                    ? "bg-white border-white/20 p-1.5"
                    : "bg-[#151D2E] border-white/10 p-2.5"
                }`}
              >
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
                  <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                    {org.name}
                  </h1>
                  {org.is_verified_government && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 text-emerald-400 px-2.5 py-0.5 text-xs font-bold border border-emerald-500/30">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      Verified Official Authority
                    </span>
                  )}
                </div>

                <div className="mt-2 flex flex-wrap items-center gap-y-1.5 gap-x-4 text-xs text-slate-400">
                  {org.office_address && (
                    <div className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-slate-500" />
                      <span>{org.office_address}</span>
                    </div>
                  )}
                  {org.official_website_url && (
                    <a
                      href={org.official_website_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-emerald-400 hover:text-emerald-300 font-medium"
                    >
                      <Globe className="w-3.5 h-3.5" />
                      <span>Official Website</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                  {org.contact_email && (
                    <div className="flex items-center gap-1">
                      <Mail className="w-3.5 h-3.5 text-slate-500" />
                      <bdi>{org.contact_email}</bdi>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Language Selection Card for Citizen */}
            <div className="w-full md:w-auto bg-[#0A0E17] border border-white/10 rounded-2xl p-4 shrink-0">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
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
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                      citizenLanguage === lang.code
                        ? "bg-emerald-500 text-slate-950 font-bold shadow-xs"
                        : "bg-[#0F1522] text-slate-300 hover:bg-[#151D2E] hover:text-white border border-white/10"
                    }`}
                  >
                    <span>{lang.nativeName}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {org.description && (
            <p className="mt-6 text-sm text-slate-300 max-w-3xl leading-relaxed border-t border-white/[0.08] pt-4">
              {org.description}
            </p>
          )}
        </div>
      </section>

      {/* Main Content Area: Published Forms Catalog */}
      <main className="max-w-6xl mx-auto px-4 pt-8">
        {startError && (
          <div className="mb-6 p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-200 text-sm flex items-center justify-between">
            <span>{startError}</span>
            <button
              onClick={() => setStartError(null)}
              aria-label="Dismiss error"
              className="text-rose-400 hover:text-rose-300 font-bold ms-4 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Guidance Banner */}
        <div className="mb-8 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5 flex items-start gap-3.5 shadow-2xs">
          <Sparkles className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="text-xs text-slate-300 space-y-1">
            <span className="font-bold text-white">
              Help Filling Out Official Forms in Your Language:
            </span>
            <p className="text-slate-300">
              Choose the form you need below. We explain every question clearly in your language, check details like dates and addresses, and prepare an official ready-to-sign PDF.
            </p>
          </div>
        </div>

        {/* Category Filter Pills (TYPO3-Inspired Multilingual Taxonomy) */}
        {org.categories && org.categories.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Filter by Category:
              </span>
              {selectedCategorySlug !== "all" && (
                <button
                  type="button"
                  onClick={() => setSelectedCategorySlug("all")}
                  className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors cursor-pointer"
                >
                  Show All ({org.published_forms.length})
                </button>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              {/* All Forms Pill */}
              <button
                type="button"
                onClick={() => setSelectedCategorySlug("all")}
                className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  selectedCategorySlug === "all"
                    ? "bg-emerald-500 text-slate-950 shadow-xs"
                    : "bg-[#0F1522] text-slate-300 hover:bg-[#151D2E] hover:text-white border border-white/10 shadow-2xs"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>{ALL_FORMS_LABELS[citizenLanguage] || ALL_FORMS_LABELS.en}</span>
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                    selectedCategorySlug === "all"
                      ? "bg-slate-950/20 text-slate-950"
                      : "bg-[#151D2E] text-slate-400"
                  }`}
                >
                  {org.published_forms.length}
                </span>
              </button>

              {/* Individual Category Pills */}
              {org.categories.map((cat) => {
                const isSelected = selectedCategorySlug === cat.slug;
                const label = getCategoryLabel(cat);
                const count = cat.forms_count;

                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setSelectedCategorySlug(cat.slug)}
                    className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                      isSelected
                        ? "bg-emerald-500 text-slate-950 shadow-xs"
                        : "bg-[#0F1522] text-slate-300 hover:bg-[#151D2E] hover:text-white border border-white/10 shadow-2xs"
                    }`}
                  >
                    <CategoryIcon name={cat.icon} className="w-3.5 h-3.5" />
                    <span>{label}</span>
                    <span
                      className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                        isSelected
                          ? "bg-slate-950/20 text-slate-950"
                          : "bg-[#151D2E] text-slate-400"
                      }`}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Search & Category Filter */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
          <div className="relative w-full sm:w-96">
            {isSearchingSemantically ? (
              <Loader2 className="pointer-events-none absolute start-3 top-2.5 w-4 h-4 text-emerald-400 animate-spin" />
            ) : (
              <Search className="pointer-events-none absolute start-3 top-2.5 w-4 h-4 text-slate-500" />
            )}
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search in your language (e.g. moving, permit, تسجيل)..."
              className="w-full rounded-xl border border-white/10 bg-[#0F1522] py-2 ps-9 pe-8 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            />
            {searchQuery.trim().length > 0 && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                aria-label="Clear search"
                className="absolute end-2.5 top-2.5 text-xs text-slate-400 hover:text-white cursor-pointer"
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {searchQuery.trim().length >= 2 && (
            <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-xl shadow-2xs">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              <span className="font-semibold">
                Smart Search in Your Language
              </span>
            </div>
          )}
        </div>

        {/* Forms Catalog Grid */}
        {filteredForms.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-[#0F1522] p-12 text-center shadow-2xs">
            <FileText className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <h3 className="text-base font-bold text-white">No Forms Found</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
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
                  className="rounded-2xl border border-white/10 bg-[#0F1522] p-6 shadow-2xs hover:shadow-md hover:border-emerald-500/40 transition-all flex flex-col justify-between"
                >
                  <div>
                    {/* Tags row */}
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                          Official Form
                        </span>
                        {form.category_name && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#151D2E] text-slate-300 border border-white/10">
                            {form.category_name}
                          </span>
                        )}
                        {form.semantic_match && (
                          <span
                            className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30"
                            title={form.semantic_match.matched_reason}
                          >
                            <Sparkles className="w-3 h-3 text-amber-400" />
                            <span>Match {Math.round(form.semantic_match.relevance_score * 100)}%</span>
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] font-mono text-slate-400">
                        {form.fields_count} Questions
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-white tracking-tight break-words">
                      {form.name}
                    </h3>

                    {form.instructions && (
                      <p className="mt-2 text-xs text-slate-400 line-clamp-2">
                        {form.instructions}
                      </p>
                    )}

                    {form.semantic_match && form.semantic_match.matched_reason && (
                      <div className="mt-2.5 p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-[11px] text-amber-200 flex items-start gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                        <span>{form.semantic_match.matched_reason}</span>
                      </div>
                    )}

                    {/* Required Documents Checklist Preview */}
                    {form.required_documents && form.required_documents.length > 0 && (
                      <div className="mt-4 pt-3.5 border-t border-white/[0.08]">
                        <span className="text-[11px] font-bold text-slate-200 flex items-center gap-1.5 mb-2">
                          <Info className="w-3.5 h-3.5 text-emerald-400" />
                          Required Supporting Documents:
                        </span>
                        <ul className="space-y-1">
                          {form.required_documents.slice(0, 3).map((doc, idx) => (
                            <li
                              key={idx}
                              className="text-xs text-slate-400 flex items-start gap-2"
                            >
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0 mt-1.5" />
                              <span className="line-clamp-1">{doc}</span>
                            </li>
                          ))}
                          {form.required_documents.length > 3 && (
                            <li className="text-[11px] text-slate-500 ps-3.5">
                              + {form.required_documents.length - 3} more items
                            </li>
                          )}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Action Button */}
                  <div className="mt-6 pt-4 border-t border-white/[0.08] flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className="text-[11px] text-emerald-400 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Free Citizen Intake
                      </span>
                      <button
                        type="button"
                        onClick={() => setSharingForm(form)}
                        className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-400 hover:text-emerald-400 transition-colors cursor-pointer"
                        title="Share Form & Counter QR Code"
                      >
                        <QrCode className="w-3.5 h-3.5" />
                        <span>QR & Share</span>
                      </button>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      {/* Language Selector on Form Card */}
                      <div className="w-48">
                        <ModernSelect
                          value={citizenLanguage}
                          onChange={(val) => {
                            setCitizenLanguage(val);
                            setLocale(val);
                          }}
                          options={UNIVERSAL_LANGUAGES.map((lang) => ({
                            value: lang.code,
                            label: `${lang.nativeName} (${lang.code.toUpperCase()})`,
                          }))}
                          size="sm"
                          aria-label="Select assistance language"
                        />
                      </div>

                      <button
                        type="button"
                        disabled={isStarting}
                        onClick={() => handleStartForm(form)}
                        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 active:scale-[0.98] text-slate-950 text-xs font-bold shadow-xs transition-all disabled:opacity-50 cursor-pointer"
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

      {sharingForm && (
        <ShareFormModal
          isOpen={!!sharingForm}
          onClose={() => setSharingForm(null)}
          form={{
            id: sharingForm.id,
            key: sharingForm.key,
            name: sharingForm.name,
          }}
          orgSlug={org?.slug}
        />
      )}
    </div>
  );
}
