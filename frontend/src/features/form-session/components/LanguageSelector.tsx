"use client";

import React, { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
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
    <div className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5 shadow-2xs space-y-4">
      {/* Top Header + Active Selection Pill */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3.5">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 border border-indigo-200/80">
              <svg
                className="h-3.5 w-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
                />
              </svg>
            </span>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
              {title}
            </h3>
          </div>
          {subtitle && (
            <p className="mt-1 text-xs text-slate-500 leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>

        {/* Current Active Language Badge */}
        <div className="inline-flex items-center gap-2 self-start sm:self-center rounded-xl border border-indigo-200 bg-indigo-50/80 px-3 py-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-md bg-indigo-600 font-mono text-[10px] font-bold uppercase text-white">
            {activeLanguage.code}
          </span>
          <div className="text-start leading-tight">
            <span className="block text-xs font-bold text-indigo-950">
              {activeLanguage.nativeName}
            </span>
            <span className="block text-[10px] font-medium text-indigo-700">
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
          <svg
            className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z"
            />
          </svg>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={tNav("searchLanguagePlaceholder")}
            aria-label="Search languages"
            className="w-full rounded-xl border border-slate-200 bg-slate-50/80 py-2 ps-9 pe-8 text-xs font-medium text-slate-900 placeholder-slate-400 transition-colors focus:border-indigo-500 focus:bg-white focus:outline-none"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              aria-label="Clear language search"
              className="absolute end-2.5 top-1/2 -translate-y-1/2 rounded-md p-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Region Filter Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto pb-0.5 sm:pb-0">
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
                    ? "bg-indigo-600 text-white shadow-2xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200/80 hover:text-slate-900"
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
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/50 py-6 text-center">
          <p className="text-xs font-medium text-slate-600">
            No language matching &ldquo;{searchQuery}&rdquo;
          </p>
          <button
            type="button"
            onClick={() => {
              setSearchQuery("");
              setActiveRegion("All");
            }}
            className="mt-2 text-xs font-semibold text-indigo-600 hover:text-indigo-800 underline"
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
                    ? "border-indigo-600 bg-indigo-50/80 text-indigo-950 ring-2 ring-indigo-600/15 shadow-2xs"
                    : "border-slate-200/90 bg-white text-slate-800 hover:border-indigo-300 hover:bg-slate-50/80"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-sm font-bold tracking-tight">
                      {lang.nativeName}
                    </span>
                    {lang.dir === "rtl" && (
                      <span className="shrink-0 rounded bg-amber-100/80 border border-amber-300/60 px-1 py-0.2 font-mono text-[9px] font-bold text-amber-900">
                        RTL
                      </span>
                    )}
                  </div>
                  <span
                    className={`block truncate text-[11px] font-medium ${
                      isSelected ? "text-indigo-700" : "text-slate-500"
                    }`}
                  >
                    {lang.englishName}
                  </span>
                </div>

                {/* Right badge: Checkmark when selected, ISO code otherwise */}
                {isSelected ? (
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white shadow-2xs">
                    <svg
                      className="h-3.5 w-3.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2.5}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </span>
                ) : (
                  <span className="shrink-0 rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase text-slate-500 group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors">
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
        <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-[11px] text-slate-500">
          <span>
            Showing {displayedLanguages.length} of {UNIVERSAL_LANGUAGES.length} supported languages
          </span>
          <button
            type="button"
            onClick={() =>
              setActiveRegion(activeRegion === "Popular" ? "All" : "Popular")
            }
            className="font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
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
