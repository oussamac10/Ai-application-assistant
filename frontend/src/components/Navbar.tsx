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
  const tNav = useTranslations("nav");

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
          l.code.toLowerCase().includes(q),
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
    return pathname === href || Boolean(pathname?.startsWith(`${href}/`));
  };

  const userDisplayHandle = user?.email.split("@")[0] || "";
  const userInitial = userDisplayHandle.charAt(0).toUpperCase() || "U";

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200/90 bg-white/95 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
        {/* Brand & Primary Nav */}
        <div className="flex min-w-0 items-center gap-4 lg:gap-6">
          <Link
            href="/"
            className="group flex shrink-0 items-center gap-2.5 rounded-lg focus-visible:outline-none"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-indigo-200/90 bg-indigo-50 text-indigo-600 shadow-2xs transition-colors group-hover:border-indigo-300 group-hover:bg-indigo-100/80">
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
            <div className="flex items-center gap-2">
              <span className="text-[15px] font-bold tracking-tight text-slate-900">
                FormFlow
              </span>
              <span className="hidden rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[10px] font-medium text-slate-500 xl:inline-block">
                Universal
              </span>
            </div>
          </Link>

          <nav
            aria-label="Primary"
            className="hidden lg:flex items-center gap-1"
          >
            <Link
              href="/"
              aria-current={isActive("/") ? "page" : undefined}
              className={`inline-flex h-9 items-center whitespace-nowrap rounded-lg px-3 text-sm transition-colors ${
                isActive("/")
                  ? "bg-indigo-50/90 font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-600/15"
                  : "font-medium text-slate-600 hover:bg-slate-100/80 hover:text-slate-900"
              }`}
            >
              {tNav("home")}
            </Link>
            <Link
              href="/application"
              aria-current={isActive("/application") ? "page" : undefined}
              className={`inline-flex h-9 items-center whitespace-nowrap rounded-lg px-3 text-sm transition-colors ${
                isActive("/application")
                  ? "bg-indigo-50/90 font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-600/15"
                  : "font-medium text-slate-600 hover:bg-slate-100/80 hover:text-slate-900"
              }`}
            >
              {tNav("newApplication")}
            </Link>
            <Link
              href="/pricing"
              aria-current={isActive("/pricing") ? "page" : undefined}
              className={`inline-flex h-9 items-center whitespace-nowrap rounded-lg px-3 text-sm transition-colors ${
                isActive("/pricing")
                  ? "bg-indigo-50/90 font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-600/15"
                  : "font-medium text-slate-600 hover:bg-slate-100/80 hover:text-slate-900"
              }`}
            >
              {tNav("pricing")}
            </Link>
            <Link
              href="/portal"
              aria-current={isActive("/portal") ? "page" : undefined}
              className={`inline-flex h-9 items-center whitespace-nowrap rounded-lg px-3 text-sm transition-colors ${
                isActive("/portal")
                  ? "bg-indigo-50/90 font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-600/15"
                  : "font-medium text-slate-600 hover:bg-slate-100/80 hover:text-slate-900"
              }`}
            >
              {tNav("agencyPortal")}
            </Link>
            {user && (
              <Link
                href="/applications"
                aria-current={isActive("/applications") ? "page" : undefined}
                className={`inline-flex h-9 items-center whitespace-nowrap rounded-lg px-3 text-sm transition-colors ${
                  isActive("/applications")
                    ? "bg-indigo-50/90 font-semibold text-indigo-700 ring-1 ring-inset ring-indigo-600/15"
                    : "font-medium text-slate-600 hover:bg-slate-100/80 hover:text-slate-900"
                }`}
              >
                {tAuth("myApplications")}
              </Link>
            )}
            {user?.role === "platform_admin" && (
              <Link
                href="/admin"
                aria-current={isActive("/admin") ? "page" : undefined}
                className={`inline-flex h-9 items-center whitespace-nowrap rounded-lg px-3 text-sm transition-colors ${
                  isActive("/admin")
                    ? "bg-amber-50 font-semibold text-amber-800 ring-1 ring-inset ring-amber-600/20"
                    : "font-medium text-amber-700 hover:bg-amber-50/80"
                }`}
              >
                {tNav("adminConsole")}
              </Link>
            )}
          </nav>
        </div>

        {/* Right Controls: Unified Searchable Language Switcher Popover & Auth */}
        <div className="flex shrink-0 items-center gap-2">
          <div className="relative" ref={popoverRef}>
            <button
              type="button"
              onClick={() => setLangPopoverOpen((prev) => !prev)}
              aria-label={tNav("changeLanguageAria", {
                name: activeLanguage.nativeName,
              })}
              aria-expanded={langPopoverOpen}
              className={`inline-flex h-9 items-center gap-2 whitespace-nowrap rounded-lg border px-2.5 text-xs font-semibold transition-all ${
                langPopoverOpen
                  ? "border-indigo-500 bg-indigo-50/80 text-indigo-900 ring-2 ring-indigo-500/15"
                  : "border-slate-200 bg-white text-slate-700 shadow-2xs hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <svg
                className="h-4 w-4 shrink-0 text-indigo-600"
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
              <span className="rounded border border-indigo-200/80 bg-indigo-50 px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase leading-none text-indigo-700">
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
              <div className="absolute end-0 z-50 mt-2 w-80 space-y-3 rounded-2xl border border-slate-200 bg-white p-3.5 shadow-xl sm:w-96">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                    {tNav("selectLanguageTitle", {
                      count: UNIVERSAL_LANGUAGES.length,
                    })}
                  </span>
                  <span className="text-[11px] font-medium text-slate-500">
                    {tNav("activeLanguage", {
                      name: activeLanguage.nativeName,
                    })}
                  </span>
                </div>

                {/* Search Input */}
                <div className="relative">
                  <svg
                    className="pointer-events-none absolute start-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400"
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
                    placeholder={tNav("searchLanguagePlaceholder")}
                    autoFocus
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 py-1.5 ps-8 pe-3 text-xs text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:bg-white focus:outline-none"
                  />
                </div>

                {/* Region Pills */}
                <div className="flex items-center gap-1 overflow-x-auto pb-0.5">
                  {[
                    { key: "Popular", label: tNav("regionPopular") },
                    {
                      key: "All",
                      label: tNav("regionAll", {
                        count: UNIVERSAL_LANGUAGES.length,
                      }),
                    },
                    { key: "Europe", label: tNav("regionEurope") },
                    { key: "Middle East & Africa", label: tNav("regionMea") },
                    { key: "Asia & Americas", label: tNav("regionAsia") },
                  ].map((tab) => {
                    const active =
                      langSearch.trim() === "" && langRegion === tab.key;
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
                <div className="grid max-h-64 grid-cols-2 gap-1.5 overflow-y-auto pe-0.5">
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
                              <span className="rounded bg-amber-100 px-1 font-mono text-[8px] font-bold text-amber-900">
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
            <div className="hidden lg:flex items-center gap-2">
              {user ? (
                <>
                  <Link
                    href="/account"
                    title={tAuth("accountSettings")}
                    aria-current={isActive("/account") ? "page" : undefined}
                    className={`inline-flex h-9 items-center gap-2 rounded-lg border px-2.5 text-xs font-semibold transition-colors ${
                      isActive("/account")
                        ? "border-indigo-300 bg-indigo-50 text-indigo-800"
                        : "border-slate-200 bg-slate-50/80 text-slate-700 hover:border-slate-300 hover:bg-slate-100"
                    }`}
                  >
                    <span
                      aria-hidden="true"
                      className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-600/10 font-mono text-[10px] font-bold text-indigo-700"
                    >
                      {userInitial}
                    </span>
                    <bdi className="max-w-[130px] truncate">
                      {userDisplayHandle}
                    </bdi>
                  </Link>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="inline-flex h-9 items-center whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-600 shadow-2xs transition-colors hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"
                  >
                    {tAuth("logout")}
                  </button>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="inline-flex h-9 items-center whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 shadow-2xs transition-colors hover:border-slate-300 hover:bg-slate-50"
                  >
                    {tAuth("loginLink")}
                  </Link>
                  <Link
                    href="/register"
                    className="inline-flex h-9 items-center whitespace-nowrap rounded-lg bg-indigo-600 px-3.5 text-xs font-semibold text-white shadow-2xs transition-colors hover:bg-indigo-700"
                  >
                    {tAuth("registerLink")}
                  </Link>
                </>
              )}
            </div>
          )}

          {/* Mobile & Tablet Menu Toggle */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 shadow-2xs hover:bg-slate-50"
            aria-label={tNav("toggleMenuAria")}
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

      {/* Mobile & Tablet Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-slate-200 bg-white px-4 py-3 space-y-1.5 shadow-lg">
          <Link
            href="/"
            onClick={() => setMobileMenuOpen(false)}
            aria-current={isActive("/") ? "page" : undefined}
            className={`block rounded-lg px-3 py-2 text-sm font-medium ${
              isActive("/")
                ? "bg-indigo-50 font-semibold text-indigo-700"
                : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            {tNav("home")}
          </Link>
          <Link
            href="/application"
            onClick={() => setMobileMenuOpen(false)}
            aria-current={isActive("/application") ? "page" : undefined}
            className={`block rounded-lg px-3 py-2 text-sm font-medium ${
              isActive("/application")
                ? "bg-indigo-50 font-semibold text-indigo-700"
                : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            {tNav("newApplication")}
          </Link>
          <Link
            href="/pricing"
            onClick={() => setMobileMenuOpen(false)}
            aria-current={isActive("/pricing") ? "page" : undefined}
            className={`block rounded-lg px-3 py-2 text-sm font-medium ${
              isActive("/pricing")
                ? "bg-indigo-50 font-semibold text-indigo-700"
                : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            {tNav("pricing")}
          </Link>
          <Link
            href="/portal"
            onClick={() => setMobileMenuOpen(false)}
            aria-current={isActive("/portal") ? "page" : undefined}
            className={`block rounded-lg px-3 py-2 text-sm font-medium ${
              isActive("/portal")
                ? "bg-indigo-50 font-semibold text-indigo-700"
                : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            {tNav("agencyPortal")}
          </Link>
          {user ? (
            <>
              <Link
                href="/applications"
                onClick={() => setMobileMenuOpen(false)}
                aria-current={isActive("/applications") ? "page" : undefined}
                className={`block rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive("/applications")
                    ? "bg-indigo-50 font-semibold text-indigo-700"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                {tAuth("myApplications")}
              </Link>
              {user.role === "platform_admin" && (
                <Link
                  href="/admin"
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive("/admin") ? "page" : undefined}
                  className={`block rounded-lg px-3 py-2 text-sm font-medium ${
                    isActive("/admin")
                      ? "bg-amber-50 font-semibold text-amber-800"
                      : "text-amber-700 hover:bg-amber-50"
                  }`}
                >
                  {tNav("adminConsole")}
                </Link>
              )}
              <Link
                href="/account"
                onClick={() => setMobileMenuOpen(false)}
                aria-current={isActive("/account") ? "page" : undefined}
                className={`block rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive("/account")
                    ? "bg-indigo-50 font-semibold text-indigo-700"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                {tAuth("accountSettings")}
              </Link>
              <button
                type="button"
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLogout();
                }}
                className="w-full rounded-lg px-3 py-2 text-start text-sm font-medium text-rose-600 hover:bg-rose-50"
              >
                {tAuth("logout")}
              </button>
            </>
          ) : (
            <div className="flex gap-2 border-t border-slate-200 pt-2">
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
