"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Sidebar from "@/components/Sidebar";
import ThemeToggle from "@/components/ThemeToggle";
import { useAuth } from "@/features/auth/context/AuthProvider";
import { useOrganization } from "@/features/portal/context/OrganizationContext";
import {
  generateBrandCssVariables,
  isCustomBrandConfig,
} from "@/features/portal/utils/theme";

interface AppShellProps {
  children: React.ReactNode;
}

// Pages that always use the public marketing layout even if logged in
const PUBLIC_MARKETING_PATHS = ["/", "/impressum", "/datenschutz", "/agb", "/pricing", "/login", "/register", "/reset-password", "/verify-email"];

export default function AppShell({ children }: AppShellProps) {
  const { user, loading } = useAuth();
  const { organization: org, effectiveThemeConfig } = useOrganization();
  const pathname = usePathname();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // While auth is loading or if user is not authenticated, render standard public layout
  if (loading || !user) {
    return (
      <div className="flex min-h-screen flex-col bg-[#0A0E17] text-slate-100">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </div>
    );
  }

  // If user is logged in, but on the public marketing landing page, legal pages, or public citizen portals
  const isMarketingPage =
    PUBLIC_MARKETING_PATHS.includes(pathname || "") ||
    Boolean(pathname?.startsWith("/organizations")) ||
    Boolean(pathname?.startsWith("/f/")) ||
    Boolean(pathname?.startsWith("/portal/invite/"));
  if (isMarketingPage) {
    return (
      <div className="flex min-h-screen flex-col bg-[#0A0E17] text-slate-100">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </div>
    );
  }

  const systemBrandVars = generateBrandCssVariables(effectiveThemeConfig);
  const isCustomBrand = isCustomBrandConfig(effectiveThemeConfig);

  // SYSTEM LAYOUT FOR LOGGED-IN USERS:
  // Persistent Left Sidebar + Top Mobile App Bar + Full Height System Workspace
  return (
    <div
      data-system-panel="true"
      data-brand-custom={isCustomBrand ? "true" : "false"}
      style={systemBrandVars as React.CSSProperties}
      className="flex h-screen w-full overflow-hidden bg-[#0A0E17] text-slate-100"
    >
      {/* Side Navigation */}
      <Sidebar
        mobileOpen={mobileSidebarOpen}
        onMobileClose={() => setMobileSidebarOpen(false)}
      />

      {/* Main System Viewport */}
      <div className="flex flex-1 flex-col min-w-0 h-full overflow-hidden">
        {/* Mobile-only Top Bar */}
        <header className="lg:hidden flex h-14 items-center justify-between px-4 bg-[#0B0F19] text-white shrink-0 border-b border-white/[0.08] shadow-sm">
          <button
            type="button"
            onClick={() => setMobileSidebarOpen(true)}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-[#151D2E]"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>
          <Link href="/portal" className="flex items-center gap-2 min-w-0">
            {org?.logo_storage_path ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={`/api/organizations/${org.id}/logo`}
                alt={org.name}
                className="w-6 h-6 rounded-md bg-white border border-slate-200 p-0.5 object-contain"
              />
            ) : null}
            <span className="text-sm font-bold tracking-tight text-white truncate max-w-[180px]">
              {org?.name ? org.name.split("—")[0].trim() : "My Workspace"}
            </span>
          </Link>
          <div className="flex items-center gap-2 shrink-0">
            <ThemeToggle variant="icon" />
            <div className="w-7 h-7 rounded-full bg-emerald-500 text-slate-950 text-xs font-bold flex items-center justify-center">
              {user.email.charAt(0).toUpperCase()}
            </div>
          </div>
        </header>

        {/* Scrollable System Content Container */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden min-w-0 bg-[#0A0E17] text-slate-100">
          {children}
        </main>
      </div>
    </div>
  );
}
