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
  User,
  ShieldCheck,
  X,
  Search,
} from "lucide-react";
import { useAuth } from "@/features/auth/context/AuthProvider";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
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
  const { locale, setLocale } = useLanguage();
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
  const roleDisplay = user?.organizationRole
    ? user.organizationRole.replace(/_/g, " ")
    : user?.role === "platform_admin"
    ? "Platform Admin"
    : "Member";

  const navLinks = [
    {
      group: "WORKSPACE",
      items: [
        {
          href: "/portal",
          label: "Triage Queue & Forms",
          icon: FolderKanban,
        },
      ],
    },
    {
      group: "APPLICATIONS",
      items: [
        {
          href: "/application",
          label: "New Application",
          icon: FilePlus,
        },
        {
          href: "/applications",
          label: "My Applications",
          icon: FileCheck,
        },
      ],
    },
    {
      group: "SETTINGS",
      items: [
        {
          href: "/account",
          label: "Workspace & Profile Vault",
          icon: Settings,
        },
        ...(user?.role === "platform_admin"
          ? [
              {
                href: "/admin",
                label: "Platform Admin Console",
                icon: ShieldAlert,
              },
            ]
          : []),
      ],
    },
  ];

  const sidebarContent = (
    <div className="flex h-full flex-col justify-between bg-[#0B0F19] text-slate-200 border-e border-[#161F30]">
      {/* Top Header: Brand & Workspace */}
      <div>
        <div className="flex h-16 items-center justify-between px-5 border-b border-[#161F30]">
          <Link href="/" className="flex items-center gap-2.5 group" title="Return to Home">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#6551f3] text-white shadow-xs group-hover:bg-[#523ee8] transition-colors">
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
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-extrabold text-white tracking-tight">
                  FormFlow
                </span>
                <span className="rounded bg-[#131B2E] border border-[#212E4A] px-1 py-0.2 font-mono text-[9px] font-bold text-[#A397F8]">
                  SYSTEM
                </span>
              </div>
            </div>
          </Link>

          {/* Close button for mobile drawer */}
          <button
            onClick={onMobileClose}
            className="lg:hidden text-slate-400 hover:text-white p-1 rounded-lg hover:bg-[#131B2E]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Workspace Quick Tag */}
        <div className="px-5 py-3 border-b border-[#161F30] bg-[#070A12]/60">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5 text-slate-300 font-semibold truncate max-w-[170px]">
              <ShieldCheck className="w-3.5 h-3.5 text-[#00c07d] shrink-0" />
              <span className="truncate">Official Agency Workspace</span>
            </div>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#A397F8] bg-[#131B2E] px-1.5 py-0.5 rounded border border-[#212E4A]">
              Live
            </span>
          </div>
        </div>

        {/* Navigation Groups */}
        <nav className="p-3 space-y-5 overflow-y-auto">
          {navLinks.map((group) => (
            <div key={group.group}>
              <div className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {group.group}
              </div>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const active = isActive(item.href);
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                        active
                          ? "bg-[#6551f3] text-white shadow-xs font-bold"
                          : "text-slate-300 hover:bg-[#131B2E] hover:text-white"
                      }`}
                    >
                      <Icon
                        className={`w-4 h-4 shrink-0 ${
                          active ? "text-white" : "text-slate-400"
                        }`}
                      />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>

      {/* Bottom Footer: Language & User Profile */}
      <div className="p-3 border-t border-[#161F30] bg-[#070A12]/80 space-y-2">
        {/* Language selector pill */}
        <button
          onClick={() => setLangModalOpen(true)}
          className="w-full flex items-center justify-between px-3 py-2 rounded-xl bg-[#131B2E]/70 hover:bg-[#131B2E] text-slate-300 hover:text-white text-xs font-medium transition-colors"
        >
          <span className="flex items-center gap-2">
            <Globe className="w-3.5 h-3.5 text-[#A397F8]" />
            <span>{activeLanguage.nativeName}</span>
          </span>
          <span className="font-mono text-[10px] font-bold text-slate-400 uppercase bg-[#0B0F19] px-1.5 py-0.5 rounded border border-[#161F30]">
            {activeLanguage.code}
          </span>
        </button>

        {/* User Card with Dropdown */}
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setUserMenuOpen((prev) => !prev)}
            className="w-full flex items-center justify-between p-2 rounded-xl hover:bg-[#131B2E] text-left transition-colors group"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-[#6551f3] text-white font-bold text-xs flex items-center justify-center shrink-0">
                {userInitial}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-white truncate">
                  {userDisplayHandle}
                </p>
                <p className="text-[10px] text-[#A397F8] font-medium capitalize truncate">
                  {roleDisplay}
                </p>
              </div>
            </div>
            <ChevronDown
              className={`w-3.5 h-3.5 text-slate-400 transition-transform ${
                userMenuOpen ? "rotate-180 text-white" : ""
              }`}
            />
          </button>

          {/* User Menu Dropdown */}
          {userMenuOpen && (
            <div className="absolute bottom-full left-0 right-0 mb-2 rounded-xl border border-[#1F2937] bg-[#111827] p-2 shadow-xl text-xs space-y-2 z-50">
              <div className="px-1.5 py-1">
                <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Signed in as</p>
                <p className="font-semibold text-white truncate text-xs mt-0.5">{user?.email}</p>
              </div>
              <div className="border-t border-[#1F2937]" />
              <button
                type="button"
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors text-left font-medium"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-slate-200 w-full max-w-md p-5 text-slate-900 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-blue-600" />
                <h3 className="text-sm font-bold text-slate-900">Select Interface Language</h3>
              </div>
              <button
                onClick={() => setLangModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                value={langSearch}
                onChange={(e) => setLangSearch(e.target.value)}
                placeholder="Search languages..."
                autoFocus
                className="w-full pl-8 pr-3 py-1.5 rounded-xl border border-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
              />
            </div>

            <div className="grid grid-cols-2 gap-1.5 max-h-64 overflow-y-auto pr-1">
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
                    className={`flex items-center justify-between p-2 rounded-xl text-left text-xs transition-colors border ${
                      isSelected
                        ? "border-blue-600 bg-blue-50 text-blue-900 font-bold"
                        : "border-slate-100 bg-slate-50 hover:bg-slate-100 text-slate-700"
                    }`}
                  >
                    <span className="truncate">{lang.nativeName}</span>
                    <span className="text-[10px] font-mono font-bold text-slate-400 uppercase">
                      {lang.code}
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
      <aside className="hidden lg:flex w-64 shrink-0 h-screen sticky top-0 z-30 border-r border-slate-800">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs"
            onClick={onMobileClose}
          />
          <div className="relative w-64 max-w-[80vw] h-full shadow-2xl z-10">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
