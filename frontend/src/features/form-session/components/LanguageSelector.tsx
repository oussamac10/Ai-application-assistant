"use client";

import React, { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Languages, Search, X, Check } from "lucide-react";
import {
  UNIVERSAL_LANGUAGES,
  POPULAR_LANGUAGE_CODES,
  LanguageOption,
  getLanguageByCode,
} from "../utils/languages";

interface LanguageSelectorProps {
  selectedCode: string;
  onSelect: (code: string) => void;
  title: string;
  subtitle?: string;
}

type RegionFilter =
  | "Popular"
  | "All"
  | "Europe"
  | "Middle East & Africa"
  | "Asia & Americas";

export default function LanguageSelector({
  selectedCode,
  onSelect,
  title,
  subtitle,
}: LanguageSelectorProps) {
  const tNav = useTranslations("nav");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeRegion, setActiveRegion] = useState<RegionFilter>("Popular");

  const regionTabs = useMemo<{ key: RegionFilter; label: string }[]>(
    () => [
      { key: "Popular", label: tNav("regionPopular") },
      { key: "All", label: tNav("regionAll", { count: UNIVERSAL_LANGUAGES.length }) },
      { key: "Europe", label: tNav("regionEurope") },
      { key: "Middle East & Africa", label: tNav("regionMea") },
      { key: "Asia & Americas", label: tNav("regionAsia") },
    ],
    [tNav]
  );

  const activeLanguage = useMemo(
    () => getLanguageByCode(selectedCode),
    [selectedCode]
  );

  const displayedLanguages = useMemo<LanguageOption[]>(() => {
    const q = searchQuery.trim().toLowerCase();
    if (q.length > 0) {
      return UNIVERSAL_LANGUAGES.filter(
        (lang) =>
          lang.nativeName.toLowerCase().includes(q) ||
          lang.englishName.toLowerCase().includes(q) ||
          lang.code.toLowerCase().includes(q) ||
          lang.region.toLowerCase().includes(q)
      );
    }

    if (activeRegion === "Popular") {
      const popularList = POPULAR_LANGUAGE_CODES.map((code) =>
        getLanguageByCode(code)
      );
      // Ensure currently selected language is always visible in Popular view
      if (!popularList.some((l) => l.code === activeLanguage.code)) {
        return [activeLanguage, ...popularList.slice(0, 7)];
      }
      return popularList;
    }

    if (activeRegion === "All") {
      return UNIVERSAL_LANGUAGES;
    }

    return UNIVERSAL_LANGUAGES.filter((lang) => lang.region === activeRegion);
  }, [searchQuery, activeRegion, activeLanguage]);

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-[#0A0E17] p-4 sm:p-5 shadow-2xs space-y-4">
      {/* Top Header + Active Selection Pill */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-3.5">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <Languages className="h-3.5 w-3.5" />
            </span>
            <h3 className="text-xs font-bold uppercase tracking-wider text-white">
              {title}
            </h3>
          </div>
          {subtitle && (
            <p className="mt-1 text-xs text-slate-400 leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>

        {/* Current Active Language Badge */}
        <div className="inline-flex items-center gap-2 self-start sm:self-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-md bg-emerald-500 font-mono text-[10px] font-bold uppercase text-slate-950">
            {activeLanguage.code}
          </span>
          <div className="text-start leading-tight">
            <span className="block text-xs font-bold text-white">
              {activeLanguage.nativeName}
            </span>
            <span className="block text-[10px] font-medium text-emerald-400">
              {activeLanguage.englishName}
              {activeLanguage.dir === "rtl" ? " • RTL" : ""}
            </span>
          </div>
        </div>
      </div>

      {/* Search Input & Region Filter Pills */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={tNav("searchLanguagePlaceholder")}
            aria-label="Search languages"
            className="w-full rounded-xl border border-white/10 bg-[#0F1522] py-2 ps-9 pe-8 text-xs font-medium text-slate-100 placeholder-slate-500 transition-colors focus:border-emerald-500 focus:bg-[#151D2E] focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/20"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              aria-label="Clear language search"
              className="absolute end-2.5 top-1/2 -translate-y-1/2 rounded-md p-0.5 text-slate-400 hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Region Filter Tabs */}
        <div className="flex flex-wrap items-center gap-1">
          {regionTabs.map((tab) => {
            const isTabActive = searchQuery.trim() === "" && activeRegion === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setActiveRegion(tab.key);
                }}
                className={`shrink-0 rounded-lg px-2.5 py-1.5 text-[11px] font-semibold transition-colors ${
                  isTabActive
                    ? "bg-emerald-500 text-slate-950 font-bold shadow-2xs"
                    : "border border-white/[0.08] bg-[#151D2E] text-slate-300 hover:bg-[#1E293B] hover:text-white"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Language Cards Grid */}
      {displayedLanguages.length === 0 ? (
        <div className="rounded-xl border border-dashed border-white/10 bg-[#0F1522] py-6 text-center">
          <p className="text-xs font-medium text-slate-400">
            No language matching &ldquo;{searchQuery}&rdquo;
          </p>
          <button
            type="button"
            onClick={() => {
              setSearchQuery("");
              setActiveRegion("All");
            }}
            className="mt-2 text-xs font-semibold text-emerald-400 hover:text-emerald-300 underline"
          >
            Show all {UNIVERSAL_LANGUAGES.length} languages
          </button>
        </div>
      ) : (
        <div
          className={`grid grid-cols-2 sm:grid-cols-4 gap-2 ${
            displayedLanguages.length > 12
              ? "max-h-64 overflow-y-auto pe-1"
              : ""
          }`}
        >
          {displayedLanguages.map((lang) => {
            const isSelected = selectedCode === lang.code;
            return (
              <button
                key={lang.code}
                type="button"
                aria-label={lang.nativeName}
                aria-pressed={isSelected}
                onClick={() => onSelect(lang.code)}
                className={`group relative flex items-center justify-between gap-2 rounded-xl border p-2.5 text-start transition-all duration-150 ${
                  isSelected
                    ? "border-emerald-500 bg-emerald-500/15 text-white ring-2 ring-emerald-500/20 shadow-2xs"
                    : "border-white/10 bg-[#0F1522] text-slate-200 hover:border-emerald-500/40 hover:bg-[#151D2E] hover:text-white"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-sm font-bold tracking-tight">
                      {lang.nativeName}
                    </span>
                    {lang.dir === "rtl" && (
                      <span className="shrink-0 rounded bg-amber-500/10 border border-amber-500/30 px-1 py-0.2 font-mono text-[9px] font-bold text-amber-300">
                        RTL
                      </span>
                    )}
                  </div>
                  <span
                    className={`block truncate text-[11px] font-medium ${
                      isSelected ? "text-emerald-300" : "text-slate-400"
                    }`}
                  >
                    {lang.englishName}
                  </span>
                </div>

                {/* Right badge: Checkmark when selected, ISO code otherwise */}
                {isSelected ? (
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-slate-950 shadow-2xs">
                    <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                  </span>
                ) : (
                  <span className="shrink-0 rounded-md border border-white/[0.08] bg-[#151D2E] px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase text-slate-400 group-hover:border-emerald-500/30 group-hover:bg-emerald-500/15 group-hover:text-emerald-400 transition-colors">
                    {lang.code}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Footer Quick Toggle between Popular & All 36 Languages */}
      {searchQuery.trim() === "" && (
        <div className="flex items-center justify-between pt-1 border-t border-white/[0.08] text-[11px] text-slate-400">
          <span>
            Showing {displayedLanguages.length} of {UNIVERSAL_LANGUAGES.length} supported languages
          </span>
          <button
            type="button"
            onClick={() =>
              setActiveRegion(activeRegion === "Popular" ? "All" : "Popular")
            }
            className="font-semibold text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            {activeRegion === "Popular"
              ? `Explore all ${UNIVERSAL_LANGUAGES.length} languages →`
              : "Show popular languages only"}
          </button>
        </div>
      )}
    </div>
  );
}
