"use client";

import React, { useState, useRef, useEffect, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  FolderKanban,
  FilePlus,
  FileCheck,
  Settings,
  ShieldAlert,
  LogOut,
  ChevronDown,
  Globe,
  X,
  Search,
  Landmark,
} from "lucide-react";
import { useAuth } from "@/features/auth/context/AuthProvider";
import { useOrganization } from "@/features/portal/context/OrganizationContext";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import { useTheme } from "@/components/ThemeProvider";
import ThemeToggle from "@/components/ThemeToggle";
import {
  resolveThemeConfig,
  getContrastTextColor,
} from "@/features/portal/utils/theme";
import {
  UNIVERSAL_LANGUAGES,
  getLanguageByCode,
} from "@/features/form-session/utils/languages";

interface SidebarProps {
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export default function Sidebar({ mobileOpen, onMobileClose }: SidebarProps) {
  const { user, logout } = useAuth();
  const { organization: org } = useOrganization();
  const { locale, setLocale } = useLanguage();
  const { theme: appTheme } = useTheme();
  const pathname = usePathname();
  const router = useRouter();
  const tNav = useTranslations("nav");

  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [langModalOpen, setLangModalOpen] = useState(false);
  const [langSearch, setLangSearch] = useState("");
  const userMenuRef = useRef<HTMLDivElement>(null);

  const activeLanguage = useMemo(() => getLanguageByCode(locale), [locale]);

  const filteredLanguages = useMemo(() => {
    const q = langSearch.trim().toLowerCase();
    if (!q) return UNIVERSAL_LANGUAGES;
    return UNIVERSAL_LANGUAGES.filter(
      (l) =>
        l.nativeName.toLowerCase().includes(q) ||
        l.englishName.toLowerCase().includes(q) ||
        l.code.toLowerCase().includes(q)
    );
  }, [langSearch]);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname === href || Boolean(pathname?.startsWith(`${href}/`));
  };

  useEffect(() => {
    onMobileClose();
    setUserMenuOpen(false);
  }, [pathname, onMobileClose]);

  useEffect(() => {
    if (!userMenuOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [userMenuOpen]);

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  const userDisplayHandle = user?.email.split("@")[0] || "User";
  const userInitial = userDisplayHandle.charAt(0).toUpperCase() || "U";
  const rawRole = org?.role || user?.organizationRole || (user?.role === "platform_admin" ? "admin" : "member");
  const roleDisplay = rawRole
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

  const theme = resolveThemeConfig(org?.ui_theme_config);
  // Always honor the user's global light/dark toggle first
  const isLight = appTheme === "light";
  const isHeraldic = appTheme !== "light" && theme.sidebar_theme === "heraldic";
  const primaryColor = theme.primary_color;
  const activeTextColor = getContrastTextColor(primaryColor);

  const orgName = org?.name || "My Organization";
  const defaultSubTitle = "Workspace";
  const [mainTitle, subTitle] = orgName.includes("—")
    ? orgName.split("—").map((s) => s.trim())
    : [orgName, defaultSubTitle];

  const navLinks = [
    {
      group: "Workspace",
      items: [
        {
          href: "/portal",
          label: "Forms & Clients",
          icon: FolderKanban,
        },
      ],
    },
    {
      group: "Forms",
      items: [
        {
          href: "/application",
          label: "Fill Out a Form",
          icon: FilePlus,
        },
        {
          href: "/applications",
          label: "My Saved Forms",
          icon: FileCheck,
        },
      ],
    },
    {
      group: "Account",
      items: [
        {
          href: "/account",
          label: "Account & Saved Details",
          icon: Settings,
        },
        ...(user?.role === "platform_admin"
          ? [
              {
                href: "/admin",
                label: "Admin Panel",
                icon: ShieldAlert,
              },
            ]
          : []),
      ],
    },
  ];

  const sidebarContent = (
    <div
      className={`flex h-full w-full min-w-0 max-w-full flex-col justify-between overflow-hidden border-e transition-colors ${
        isLight
          ? "bg-white text-slate-800 border-slate-200"
          : isHeraldic
          ? "bg-[#0b1329] text-slate-100 border-[#1c2c54]"
          : "bg-[#0B0F19] text-slate-200 border-[#161F30]"
      }`}
    >
      {/* Top Header: Brand & Workspace */}
      <div className="min-w-0 flex flex-col flex-1 overflow-hidden">
        <div
          className={`flex h-16 shrink-0 items-center justify-between px-4 border-b min-w-0 ${
            isLight
              ? "border-slate-200"
              : isHeraldic
              ? "border-[#1c2c54]"
              : "border-[#161F30]"
          }`}
        >
          <Link href="/portal" className="flex items-center gap-2.5 group min-w-0 flex-1 overflow-hidden" title="Go to Forms & Clients">
            <div
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border p-1 shadow-xs overflow-hidden ${
                org?.logo_storage_path
                  ? isLight
                    ? "bg-white border-slate-200"
                    : "bg-white border-white/15"
                  : isLight
                  ? "bg-slate-100 border-slate-200"
                  : "bg-[#131B2E] border-white/15"
              }`}
            >
              {org?.logo_storage_path ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={`/api/organizations/${org.id}/logo`}
                  alt={`${org.name} logo`}
                  className="h-full w-full object-contain"
                />
              ) : (
                <Landmark className={`h-5 w-5 ${isLight ? "text-emerald-700" : "text-emerald-400"}`} />
              )}
            </div>
            <div className="min-w-0 flex-1 overflow-hidden">
              <div className="flex items-center gap-1.5 min-w-0">
                <span
                  className={`text-xs font-bold tracking-tight truncate min-w-0 ${
                    isLight ? "text-slate-900" : "text-white"
                  }`}
                >
                  {mainTitle}
                </span>
              </div>
              <div
                className={`text-[10px] truncate font-medium min-w-0 ${
                  isLight ? "text-slate-500" : "text-slate-400"
                }`}
              >
                {subTitle}
              </div>
            </div>
          </Link>

          {/* Close button for mobile drawer */}
          <button
            onClick={onMobileClose}
            className={`lg:hidden p-1 rounded-lg shrink-0 ${
              isLight
                ? "text-slate-500 hover:text-slate-900 hover:bg-slate-100"
                : "text-slate-400 hover:text-white hover:bg-[#131B2E]"
            }`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Workspace Quick Tag */}
        <div
          className={`px-4 py-2.5 shrink-0 border-b min-w-0 ${
            isLight
              ? "bg-slate-50 border-slate-200"
              : isHeraldic
              ? "bg-[#070e20] border-[#1c2c54]"
              : "bg-[#070A12]/60 border-[#161F30]"
          }`}
        >
          <div className="flex items-center justify-between text-xs min-w-0 gap-2">
            <div className="flex items-center gap-1.5 font-semibold truncate min-w-0">
              <span className="flex h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
              <span className={`truncate text-[11px] min-w-0 ${isLight ? "text-emerald-700" : "text-emerald-400"}`}>
                {org?.is_verified_government ? "Verified Office" : "Active Workspace"}
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Groups */}
        <nav className="p-3 space-y-5 overflow-y-auto overflow-x-hidden min-w-0 flex-1">
          {navLinks.map((group) => (
            <div key={group.group} className="min-w-0">
              <div
                className={`px-3 mb-1.5 text-[11px] font-semibold tracking-wide truncate ${
                  isLight ? "text-slate-500" : "text-slate-400"
                }`}
              >
                {group.group}
              </div>
              <div className="space-y-1 min-w-0">
                {group.items.map((item) => {
                  const active = isActive(item.href);
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      style={
                        active
                          ? {
                              backgroundColor: primaryColor,
                              color: activeTextColor,
                            }
                          : undefined
                      }
                      className={`flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all min-w-0 ${
                        active
                          ? "shadow-xs font-bold"
                          : isLight
                          ? "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                          : "text-slate-300 hover:bg-[#131B2E] hover:text-white"
                      }`}
                    >
                      <Icon
                        className="w-4 h-4 shrink-0"
                        style={active ? { color: activeTextColor } : undefined}
                      />
                      <span className="truncate min-w-0">{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>

      {/* Bottom Footer: Theme, Language & User Profile */}
      <div
        className={`p-3 shrink-0 border-t space-y-2 ${
          isLight
            ? "border-slate-200 bg-slate-50/80"
            : isHeraldic
            ? "border-[#1c2c54] bg-[#070e20]"
            : "border-[#161F30] bg-[#070A12]/80"
        }`}
      >
        <ThemeToggle variant="pill" />

        {/* Language selector pill */}
        <button
          onClick={() => setLangModalOpen(true)}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-colors ${
            isLight
              ? "bg-slate-100 hover:bg-slate-200/80 text-slate-700 hover:text-slate-900"
              : "bg-[#131B2E]/70 hover:bg-[#131B2E] text-slate-300 hover:text-white"
          }`}
        >
          <span className="flex items-center gap-2">
            <Globe className={`w-3.5 h-3.5 ${isLight ? "text-emerald-700" : "text-emerald-400"}`} />
            <span>{activeLanguage.nativeName}</span>
          </span>
          <ChevronDown className={`w-3.5 h-3.5 ${isLight ? "text-slate-500" : "text-slate-400"}`} />
        </button>

        {/* User Card with Dropdown */}
        <div className="relative min-w-0" ref={userMenuRef}>
          <button
            onClick={() => setUserMenuOpen((prev) => !prev)}
            className={`w-full flex items-center justify-between p-2 rounded-xl text-left transition-colors group min-w-0 ${
              isLight ? "hover:bg-slate-100" : "hover:bg-[#131B2E]"
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0 flex-1">
              <div className="w-8 h-8 rounded-full bg-emerald-500 text-slate-950 font-bold text-xs flex items-center justify-center shrink-0">
                {userInitial}
              </div>
              <div className="min-w-0 flex-1">
                <p className={`text-xs font-bold truncate ${isLight ? "text-slate-900" : "text-white"}`}>
                  {userDisplayHandle}
                </p>
                <p
                  className={`text-[11px] font-medium truncate ${
                    isLight ? "text-emerald-700" : "text-emerald-400"
                  }`}
                >
                  {roleDisplay}
                </p>
              </div>
            </div>
            <ChevronDown
              className={`w-3.5 h-3.5 text-slate-400 transition-transform shrink-0 ${
                userMenuOpen ? (isLight ? "rotate-180 text-slate-900" : "rotate-180 text-white") : ""
              }`}
            />
          </button>

          {/* User Menu Dropdown */}
          {userMenuOpen && (
            <div className="absolute bottom-full inset-x-0 mb-2 rounded-xl border border-white/10 bg-[#0F1522] p-2 shadow-2xl text-xs space-y-2 z-50">
              <div className="px-1.5 py-1">
                <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Signed in as</p>
                <p className="font-semibold text-white truncate text-xs mt-0.5">{user?.email}</p>
              </div>
              <div className="border-t border-white/10" />
              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 transition-colors text-left font-medium"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Log out</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Language Selector Modal */}
      {langModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-[#0F1522] rounded-2xl border border-white/15 w-full max-w-md p-5 text-slate-100 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">Select Interface Language</h3>
              </div>
              <button
                onClick={() => setLangModalOpen(false)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="relative">
              <Search className="pointer-events-none absolute start-3 top-2.5 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                value={langSearch}
                onChange={(e) => setLangSearch(e.target.value)}
                placeholder="Search languages..."
                autoFocus
                className="w-full ps-8 pe-3 py-1.5 rounded-xl border border-white/10 bg-[#0A0E17] text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>

            <div className="grid grid-cols-2 gap-1.5 max-h-64 overflow-y-auto pe-1">
              {filteredLanguages.map((lang) => {
                const isSelected = locale === lang.code;
                return (
                  <button
                    key={lang.code}
                    onClick={() => {
                      setLocale(lang.code);
                      setLangModalOpen(false);
                      setLangSearch("");
                    }}
                    className={`flex flex-col items-start p-2 rounded-xl text-left text-xs transition-colors border ${
                      isSelected
                        ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-300 font-bold"
                        : "border-white/[0.08] bg-[#0A0E17] hover:bg-[#151D2E] text-slate-300 hover:text-white"
                    }`}
                  >
                    <span className="truncate font-semibold">{lang.nativeName}</span>
                    <span className="truncate text-[10px] text-slate-400">
                      {lang.englishName}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden lg:flex w-64 shrink-0 h-full overflow-hidden z-20">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs animate-in fade-in duration-200"
            onClick={onMobileClose}
          />
          <div className="relative start-0 w-64 max-w-[80vw] h-full shadow-2xl z-10 animate-in slide-in-from-left rtl:slide-in-from-right duration-200">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
