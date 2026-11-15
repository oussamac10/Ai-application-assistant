"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  ChevronDown,
  FileText,
  FolderKanban,
  Languages,
  LogOut,
  Menu,
  Search,
  Settings,
  ShieldCheck,
  X,
} from "lucide-react";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import {
  UNIVERSAL_LANGUAGES,
  POPULAR_LANGUAGE_CODES,
  getLanguageByCode,
} from "@/features/form-session/utils/languages";
import { useAuth } from "@/features/auth/context/AuthProvider";
import ThemeToggle from "@/components/ThemeToggle";

export default function Navbar() {
  const { locale, setLocale } = useLanguage();
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const tAuth = useTranslations("auth");
  const tNav = useTranslations("nav");

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [langPopoverOpen, setLangPopoverOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [langSearch, setLangSearch] = useState("");
  const [langRegion, setLangRegion] = useState<string>("Popular");
  const popoverRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (!userMenuOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(event.target as Node)
      ) {
        setUserMenuOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [userMenuOpen]);

  useEffect(() => {
    setUserMenuOpen(false);
    setMobileMenuOpen(false);
    setLangPopoverOpen(false);
  }, [pathname]);

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
    <header className="sticky top-0 z-50 w-full border-b border-white/[0.08] bg-[#0A0E17]/95 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-2.5 sm:gap-4 px-4 sm:px-6 lg:px-8">
        {/* Brand & Primary Nav */}
        <div className="flex min-w-0 items-center gap-3 lg:gap-5 xl:gap-6">
          <Link
            href="/"
            className="group flex shrink-0 items-center gap-2.5 rounded-lg focus-visible:outline-none"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 shadow-[0_0_12px_rgb(var(--brand-500-rgb)/0.25)] transition-colors group-hover:border-emerald-500/50 group-hover:bg-emerald-500/20">
              <FileText className="h-4 w-4" />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[15px] font-bold tracking-tight text-white">
                FormFlow
              </span>
            </div>
          </Link>

          <nav
            aria-label="Primary"
            className="hidden lg:flex items-center gap-1 xl:gap-2"
          >
            <Link
              href="/"
              aria-current={isActive("/") ? "page" : undefined}
              className={`inline-flex h-9 shrink-0 items-center whitespace-nowrap rounded-lg px-2.5 xl:px-3 text-xs xl:text-sm transition-colors ${
                isActive("/")
                  ? "border border-emerald-500/30 bg-emerald-500/10 font-semibold text-emerald-300"
                  : "font-medium text-slate-300 hover:bg-white/[0.05] hover:text-white"
              }`}
            >
              {tNav("home")}
            </Link>
            {!user && (
              <Link
                href="/application"
                aria-current={isActive("/application") ? "page" : undefined}
                className={`inline-flex h-9 shrink-0 items-center whitespace-nowrap rounded-lg px-2.5 xl:px-3 text-xs xl:text-sm transition-colors ${
                  isActive("/application")
                    ? "border border-emerald-500/30 bg-emerald-500/10 font-semibold text-emerald-300"
                    : "font-medium text-slate-300 hover:bg-white/[0.05] hover:text-white"
                }`}
              >
                {tNav("newApplication")}
              </Link>
            )}
            <Link
              href="/pricing"
              aria-current={isActive("/pricing") ? "page" : undefined}
              className={`inline-flex h-9 shrink-0 items-center whitespace-nowrap rounded-lg px-2.5 xl:px-3 text-xs xl:text-sm transition-colors ${
                isActive("/pricing")
                  ? "border border-emerald-500/30 bg-emerald-500/10 font-semibold text-emerald-300"
                  : "font-medium text-slate-300 hover:bg-white/[0.05] hover:text-white"
              }`}
            >
              {tNav("pricing")}
            </Link>
            <Link
              href="/organizations"
              aria-current={isActive("/organizations") ? "page" : undefined}
              className={`inline-flex h-9 shrink-0 items-center whitespace-nowrap rounded-lg px-2.5 xl:px-3 text-xs xl:text-sm transition-colors ${
                isActive("/organizations")
                  ? "border border-emerald-500/30 bg-emerald-500/10 font-semibold text-emerald-300"
                  : "font-medium text-slate-300 hover:bg-white/[0.05] hover:text-white"
              }`}
            >
              Public Forms
            </Link>
          </nav>
        </div>

        {/* Right Controls: Theme Switcher, Unified Language Switcher & Auth */}
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <ThemeToggle variant="icon" />

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
                  ? "border-emerald-500 bg-[#151D2E] text-white ring-2 ring-emerald-500/20"
                  : "border-white/[0.12] bg-[#0F1522] text-slate-200 shadow-2xs hover:border-emerald-500/40 hover:bg-[#151D2E] hover:text-white"
              }`}
            >
              <Languages className="h-4 w-4 shrink-0 text-emerald-400" />
              <span className="font-bold text-slate-100">
                {activeLanguage.nativeName}
              </span>
              <ChevronDown
                className={`h-3.5 w-3.5 text-slate-400 transition-transform ${
                  langPopoverOpen ? "rotate-180 text-emerald-400" : ""
                }`}
              />
            </button>

            {/* Floating Searchable Language Popover */}
            {langPopoverOpen && (
              <div className="absolute end-0 z-50 mt-2 w-80 space-y-3 rounded-2xl border border-white/[0.12] bg-[#0F1522] p-3.5 shadow-[0_20px_50px_rgba(0,0,0,0.85)] sm:w-96 backdrop-blur-xl">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-2">
                  <span className="text-xs font-bold text-slate-300">
                    {tNav("selectLanguageTitle", {
                      count: UNIVERSAL_LANGUAGES.length,
                    })}
                  </span>
                  <span className="text-[11px] font-medium text-emerald-400">
                    {tNav("activeLanguage", {
                      name: activeLanguage.nativeName,
                    })}
                  </span>
                </div>

                {/* Search Input */}
                <div className="relative">
                  <Search className="pointer-events-none absolute start-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text"
                    value={langSearch}
                    onChange={(e) => setLangSearch(e.target.value)}
                    placeholder={tNav("searchLanguagePlaceholder")}
                    autoFocus
                    className="w-full rounded-lg border border-white/[0.1] bg-[#0A0E17] py-1.5 ps-8 pe-3 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:bg-[#0A0E17] focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/30"
                  />
                </div>

                {/* Region Pills */}
                <div className="flex flex-wrap items-center gap-1">
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
                            ? "bg-emerald-500 text-slate-950 font-bold"
                            : "bg-[#151D2E] text-slate-400 hover:bg-[#1E293B] hover:text-slate-200 border border-white/[0.06]"
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
                            ? "border-emerald-500/70 bg-emerald-500/10 text-emerald-300"
                            : "border-white/[0.08] bg-[#0A0E17]/70 text-slate-300 hover:border-emerald-500/30 hover:bg-[#151D2E]"
                        }`}
                      >
                        <div className="min-w-0">
                          <span className="block truncate text-xs font-bold">
                            {lang.nativeName}
                          </span>
                          <span className="block truncate text-[10px] text-slate-400">
                            {lang.englishName}
                          </span>
                        </div>
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
                <div className="relative" ref={userMenuRef}>
                  <button
                    type="button"
                    onClick={() => setUserMenuOpen((prev) => !prev)}
                    aria-expanded={userMenuOpen}
                    aria-haspopup="menu"
                    aria-label="User account menu"
                    className={`inline-flex h-9 items-center gap-2 rounded-xl border px-2.5 text-xs font-semibold transition-all ${
                      userMenuOpen
                        ? "border-emerald-500 bg-[#151D2E] text-white ring-2 ring-emerald-500/20"
                        : "border-white/[0.12] bg-[#0F1522] text-slate-200 shadow-2xs hover:border-emerald-500/40 hover:bg-[#151D2E]"
                    }`}
                  >
                    <span
                      aria-hidden="true"
                      className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500 font-mono text-[10px] font-bold text-slate-950 shadow-2xs"
                    >
                      {userInitial}
                    </span>
                    <bdi className="max-w-[120px] truncate text-slate-100 font-bold">
                      {userDisplayHandle}
                    </bdi>
                    {user.organizationRole && (
                      <span className="hidden xl:inline-block rounded bg-[#151D2E] border border-white/[0.1] px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 capitalize">
                        {user.organizationRole.replace("_", " ")}
                      </span>
                    )}
                    <ChevronDown
                      className={`h-3.5 w-3.5 text-slate-400 transition-transform ${
                        userMenuOpen ? "rotate-180 text-emerald-400" : ""
                      }`}
                    />
                  </button>

                  {/* Floating User Profile Dropdown Menu */}
                  {userMenuOpen && (
                    <div
                      role="menu"
                      className="absolute end-0 z-50 mt-2 w-64 divide-y divide-white/[0.08] rounded-2xl border border-white/[0.12] bg-[#0F1522] py-1.5 shadow-[0_20px_50px_rgba(0,0,0,0.85)] ring-1 ring-white/5 backdrop-blur-xl"
                    >
                      {/* Identity & Workspace Role Header */}
                      <div className="px-3.5 py-2.5 text-start">
                        <p className="text-[11px] font-medium text-slate-400">Signed in as</p>
                        <p className="truncate text-xs font-bold text-white mt-0.5" title={user.email}>
                          {user.email}
                        </p>
                        <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                          <span className="inline-flex items-center rounded-md bg-[#151D2E] border border-white/[0.08] px-1.5 py-0.5 text-[10px] font-semibold text-slate-300 capitalize">
                            {user.accountType ?? "Individual"}
                          </span>
                          {user.organizationRole && (
                            <span className="inline-flex items-center rounded-md bg-emerald-500/10 border border-emerald-500/25 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 capitalize">
                              {user.organizationRole.replace(/_/g, " ")}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Workspace & Management Links */}
                      <div className="py-1 text-start">
                        <Link
                          href="/portal"
                          role="menuitem"
                          onClick={() => setUserMenuOpen(false)}
                          className="flex w-full items-center gap-2.5 px-3.5 py-2 text-xs font-bold text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300 transition-colors"
                        >
                          <FolderKanban className="h-4 w-4 text-emerald-400 shrink-0" />
                          <span>Workspace</span>
                        </Link>
                        <Link
                          href="/account"
                          role="menuitem"
                          onClick={() => setUserMenuOpen(false)}
                          className="flex w-full items-center gap-2.5 px-3.5 py-2 text-xs font-semibold text-slate-300 hover:bg-white/[0.05] hover:text-white transition-colors"
                        >
                          <Settings className="h-4 w-4 text-slate-400 shrink-0" />
                          <span>{tAuth("accountSettings")}</span>
                        </Link>
                        {user.role === "platform_admin" && (
                          <Link
                            href="/admin"
                            role="menuitem"
                            onClick={() => setUserMenuOpen(false)}
                            className="flex w-full items-center gap-2.5 px-3.5 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-500/10 transition-colors"
                          >
                            <ShieldCheck className="h-4 w-4 text-amber-400 shrink-0" />
                            <span>{tNav("adminConsole")}</span>
                          </Link>
                        )}
                      </div>

                      {/* Logout Option */}
                      <div className="py-1 text-start">
                        <button
                          type="button"
                          role="menuitem"
                          onClick={async () => {
                            setUserMenuOpen(false);
                            await handleLogout();
                          }}
                          className="flex w-full items-center gap-2.5 px-3.5 py-2 text-xs font-semibold text-rose-400 hover:bg-rose-500/10 transition-colors"
                        >
                          <LogOut className="h-4 w-4 text-rose-400 shrink-0" />
                          <span>{tAuth("logout")}</span>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="inline-flex h-9 items-center whitespace-nowrap rounded-lg border border-white/[0.12] bg-[#0F1522] px-3 text-xs font-semibold text-slate-200 shadow-2xs transition-colors hover:border-emerald-500/40 hover:bg-[#151D2E] hover:text-white"
                  >
                    {tAuth("loginLink")}
                  </Link>
                  <Link
                    href="/register"
                    className="inline-flex h-9 items-center whitespace-nowrap rounded-lg bg-emerald-500 px-3.5 text-xs font-bold text-slate-950 shadow-[0_0_15px_rgb(var(--brand-500-rgb)/0.3)] transition-colors hover:bg-emerald-400"
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
            className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-lg border border-white/[0.12] bg-[#0F1522] text-slate-300 shadow-2xs hover:bg-[#151D2E] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500"
            aria-label={tNav("toggleMenuAria")}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? (
              <X className="h-4 w-4" />
            ) : (
              <Menu className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile & Tablet Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-white/[0.08] bg-[#0A0E17] px-4 py-3 space-y-1.5 shadow-2xl">
          <div className="pt-1 pb-2 border-b border-white/[0.08]">
            <ThemeToggle variant="pill" />
          </div>
          <Link
            href="/"
            onClick={() => setMobileMenuOpen(false)}
            aria-current={isActive("/") ? "page" : undefined}
            className={`block rounded-lg px-3 py-2 text-sm font-medium ${
              isActive("/")
                ? "border border-emerald-500/30 bg-emerald-500/10 font-semibold text-emerald-300"
                : "text-slate-200 hover:bg-[#151D2E]"
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
                ? "border border-emerald-500/30 bg-emerald-500/10 font-semibold text-emerald-300"
                : "text-slate-200 hover:bg-[#151D2E]"
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
                ? "border border-emerald-500/30 bg-emerald-500/10 font-semibold text-emerald-300"
                : "text-slate-200 hover:bg-[#151D2E]"
            }`}
          >
            {tNav("pricing")}
          </Link>
          <Link
            href="/organizations"
            onClick={() => setMobileMenuOpen(false)}
            aria-current={isActive("/organizations") ? "page" : undefined}
            className={`block rounded-lg px-3 py-2 text-sm font-medium ${
              isActive("/organizations")
                ? "border border-emerald-500/30 bg-emerald-500/10 font-semibold text-emerald-300"
                : "text-slate-200 hover:bg-[#151D2E]"
            }`}
          >
            Public Forms
          </Link>
          {user ? (
            <>
              <Link
                href="/portal"
                onClick={() => setMobileMenuOpen(false)}
                aria-current={isActive("/portal") ? "page" : undefined}
                className="block rounded-lg px-3 py-2 text-sm font-bold bg-emerald-500 text-slate-950"
              >
                Go to Workspace →
              </Link>
              <Link
                href="/account"
                onClick={() => setMobileMenuOpen(false)}
                aria-current={isActive("/account") ? "page" : undefined}
                className={`block rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive("/account")
                    ? "bg-emerald-500/10 text-emerald-300 font-semibold"
                    : "text-slate-200 hover:bg-[#151D2E]"
                }`}
              >
                {tAuth("accountSettings")}
              </Link>
              {user.role === "platform_admin" && (
                <Link
                  href="/admin"
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive("/admin") ? "page" : undefined}
                  className="block rounded-lg px-3 py-2 text-sm font-medium text-amber-300 hover:bg-amber-500/10"
                >
                  {tNav("adminConsole")}
                </Link>
              )}
              <button
                type="button"
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLogout();
                }}
                className="w-full rounded-lg px-3 py-2 text-start text-sm font-medium text-rose-400 hover:bg-rose-500/10"
              >
                {tAuth("logout")}
              </button>
            </>
          ) : (
            <div className="flex gap-2 border-t border-white/[0.08] pt-2">
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
