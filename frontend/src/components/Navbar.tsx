"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import {
  UNIVERSAL_LANGUAGES,
  POPULAR_LANGUAGE_CODES,
  getLanguageByCode,
} from "@/features/form-session/utils/languages";
import { useAuth } from "@/features/auth/context/AuthProvider";

export default function Navbar() {
  const { locale, setLocale } = useLanguage();
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const tAuth = useTranslations("auth");

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [langPopoverOpen, setLangPopoverOpen] = useState(false);
  const [langSearch, setLangSearch] = useState("");
  const [langRegion, setLangRegion] = useState<string>("Popular");
  const popoverRef = useRef<HTMLDivElement>(null);

  const activeLanguage = useMemo(() => getLanguageByCode(locale), [locale]);

  const filteredPopoverLanguages = useMemo(() => {
    const q = langSearch.trim().toLowerCase();
    if (q.length > 0) {
      return UNIVERSAL_LANGUAGES.filter(
        (l) =>
          l.nativeName.toLowerCase().includes(q) ||
          l.englishName.toLowerCase().includes(q) ||
          l.code.toLowerCase().includes(q)
      );
    }
    if (langRegion === "Popular") {
      return POPULAR_LANGUAGE_CODES.map((code) => getLanguageByCode(code));
    }
    if (langRegion === "All") {
      return UNIVERSAL_LANGUAGES;
    }
    return UNIVERSAL_LANGUAGES.filter((l) => l.region === langRegion);
  }, [langSearch, langRegion]);

  useEffect(() => {
    if (!langPopoverOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(event.target as Node)
      ) {
        setLangPopoverOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setLangPopoverOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [langPopoverOpen]);

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname?.startsWith(href);
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/95 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand & Primary Nav */}
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="group flex items-center gap-2.5 rounded-lg focus-visible:outline-none"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-indigo-200 bg-indigo-50 text-indigo-600 transition-colors group-hover:border-indigo-300 group-hover:bg-indigo-100">
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-bold tracking-tight text-slate-900">
                FormFlow
              </span>
              <span className="hidden rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[10px] font-medium text-slate-600 sm:inline-block">
                Universal
              </span>
            </div>
          </Link>

          <nav
            aria-label="Primary"
            className="hidden md:flex items-center gap-1 text-sm"
          >
            <Link
              href="/"
              aria-current={isActive("/") ? "page" : undefined}
              className={`rounded-lg px-3 py-1.5 font-medium transition-colors ${
                isActive("/")
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              Home
            </Link>
            <Link
              href="/application"
              aria-current={isActive("/application") ? "page" : undefined}
              className={`rounded-lg px-3 py-1.5 font-medium transition-colors ${
                isActive("/application")
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              New Application
            </Link>
            {user && (
              <Link
                href="/applications"
                aria-current={isActive("/applications") ? "page" : undefined}
                className={`rounded-lg px-3 py-1.5 font-medium transition-colors ${
                  isActive("/applications")
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {tAuth("myApplications")}
              </Link>
            )}
          </nav>
        </div>

        {/* Right Controls: Unified Searchable Language Switcher Popover & Auth */}
        <div className="flex items-center gap-2.5">
          <div className="relative" ref={popoverRef}>
            <button
              type="button"
              onClick={() => setLangPopoverOpen((prev) => !prev)}
              aria-label={`Change interface language (${activeLanguage.nativeName})`}
              aria-expanded={langPopoverOpen}
              className={`inline-flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-semibold transition-all ${
                langPopoverOpen
                  ? "border-indigo-500 bg-indigo-50/70 text-indigo-900 ring-2 ring-indigo-500/15"
                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50 shadow-2xs"
              }`}
            >
              <svg
                className="h-4 w-4 text-indigo-600 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.75}
                  d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
                />
              </svg>
              <span className="font-bold text-slate-900">
                {activeLanguage.nativeName}
              </span>
              <span className="rounded bg-indigo-50 border border-indigo-200/80 px-1.5 py-0.2 font-mono text-[10px] font-bold uppercase text-indigo-700">
                {activeLanguage.code}
              </span>
              <svg
                className={`h-3.5 w-3.5 text-slate-400 transition-transform ${
                  langPopoverOpen ? "rotate-180" : ""
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            {/* Floating Searchable Language Popover */}
            {langPopoverOpen && (
              <div className="absolute end-0 mt-2 w-80 sm:w-96 rounded-2xl border border-slate-200 bg-white p-3.5 shadow-xl z-50 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    Select Your Language ({UNIVERSAL_LANGUAGES.length})
                  </span>
                  <span className="text-[11px] font-medium text-slate-500">
                    Active: {activeLanguage.englishName}
                  </span>
                </div>

                {/* Search Input */}
                <div className="relative">
                  <svg
                    className="pointer-events-none absolute start-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400"
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
                    value={langSearch}
                    onChange={(e) => setLangSearch(e.target.value)}
                    placeholder="Search language (e.g. العربية, Deutsch, Türkçe)..."
                    autoFocus
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 py-1.5 ps-8 pe-3 text-xs text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:bg-white focus:outline-none"
                  />
                </div>

                {/* Region Pills */}
                <div className="flex items-center gap-1 overflow-x-auto pb-0.5">
                  {[
                    { key: "Popular", label: "Popular" },
                    { key: "All", label: `All (${UNIVERSAL_LANGUAGES.length})` },
                    { key: "Europe", label: "Europe" },
                    { key: "Middle East & Africa", label: "MEA" },
                    { key: "Asia & Americas", label: "Asia" },
                  ].map((tab) => {
                    const active = langSearch.trim() === "" && langRegion === tab.key;
                    return (
                      <button
                        key={tab.key}
                        type="button"
                        onClick={() => {
                          setLangSearch("");
                          setLangRegion(tab.key);
                        }}
                        className={`shrink-0 rounded-md px-2 py-1 text-[11px] font-semibold transition-colors ${
                          active
                            ? "bg-indigo-600 text-white"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {tab.label}
                      </button>
                    );
                  })}
                </div>

                {/* Language List */}
                <div className="grid grid-cols-2 gap-1.5 max-h-64 overflow-y-auto pe-0.5">
                  {filteredPopoverLanguages.map((lang) => {
                    const isSelected = locale === lang.code;
                    return (
                      <button
                        key={lang.code}
                        type="button"
                        onClick={() => {
                          setLocale(lang.code);
                          setLangPopoverOpen(false);
                          setLangSearch("");
                        }}
                        className={`flex items-center justify-between gap-2 rounded-xl border p-2 text-start transition-colors ${
                          isSelected
                            ? "border-indigo-600 bg-indigo-50/90 text-indigo-950"
                            : "border-slate-200/80 bg-white text-slate-800 hover:border-indigo-300 hover:bg-slate-50"
                        }`}
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-1">
                            <span className="truncate text-xs font-bold">
                              {lang.nativeName}
                            </span>
                            {lang.dir === "rtl" && (
                              <span className="rounded bg-amber-100 px-1 text-[8px] font-mono font-bold text-amber-900">
                                RTL
                              </span>
                            )}
                          </div>
                          <span className="block truncate text-[10px] text-slate-500">
                            {lang.englishName}
                          </span>
                        </div>
                        <span
                          className={`shrink-0 rounded px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase ${
                            isSelected
                              ? "bg-indigo-600 text-white"
                              : "bg-slate-100 text-slate-500"
                          }`}
                        >
                          {lang.code}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {!loading && (
            <div className="hidden sm:flex items-center gap-2">
              {user ? (
                <>
                  <Link
                    href="/applications"
                    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-100"
                  >
                    {user.email.split("@")[0]}
                  </Link>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition-colors hover:border-rose-300 hover:bg-rose-50 hover:text-rose-700"
                  >
                    {tAuth("logout")}
                  </button>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50"
                  >
                    {tAuth("loginLink")}
                  </Link>
                  <Link
                    href="/register"
                    className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700"
                  >
                    {tAuth("registerLink")}
                  </Link>
                </>
              )}
            </div>
          )}

          {/* Mobile Menu Toggle */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden rounded-lg border border-slate-200 bg-white p-2 text-slate-700 hover:bg-slate-50"
            aria-label="Toggle menu"
            aria-expanded={mobileMenuOpen}
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              {mobileMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 py-3 space-y-1.5 shadow-lg">
          <Link
            href="/"
            onClick={() => setMobileMenuOpen(false)}
            className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            Home
          </Link>
          <Link
            href="/application"
            onClick={() => setMobileMenuOpen(false)}
            className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            New Application
          </Link>
          {user ? (
            <>
              <Link
                href="/applications"
                onClick={() => setMobileMenuOpen(false)}
                className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
              >
                {tAuth("myApplications")}
              </Link>
              <button
                type="button"
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLogout();
                }}
                className="w-full text-start rounded-lg px-3 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50"
              >
                {tAuth("logout")}
              </button>
            </>
          ) : (
            <div className="flex gap-2 pt-2 border-t border-slate-200">
              <Link
                href="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="btn-secondary flex-1 py-2 text-xs"
              >
                {tAuth("loginLink")}
              </Link>
              <Link
                href="/register"
                onClick={() => setMobileMenuOpen(false)}
                className="btn-primary flex-1 py-2 text-xs"
              >
                {tAuth("registerLink")}
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
