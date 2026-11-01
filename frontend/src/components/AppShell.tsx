"use client";

import React, { useState } from "react";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Sidebar from "@/components/Sidebar";
import { useAuth } from "@/features/auth/context/AuthProvider";

interface AppShellProps {
  children: React.ReactNode;
}

// Pages that always use the public marketing layout even if logged in
const PUBLIC_MARKETING_PATHS = ["/", "/impressum", "/datenschutz", "/agb", "/pricing", "/login", "/register", "/reset-password", "/verify-email"];

export default function AppShell({ children }: AppShellProps) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // While auth is loading or if user is not authenticated, render standard public layout
  if (loading || !user) {
    return (
      <div className="flex min-h-screen flex-col bg-[#f8fafc]">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </div>
    );
  }

  // If user is logged in, but on the public marketing landing page or legal pages
  const isMarketingPage = PUBLIC_MARKETING_PATHS.includes(pathname || "");
  if (isMarketingPage) {
    return (
      <div className="flex min-h-screen flex-col bg-[#f8fafc]">
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </div>
    );
  }

  // SYSTEM LAYOUT FOR LOGGED-IN USERS:
  // Persistent Left Sidebar + Top Mobile App Bar + Full Height System Workspace
  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-100/70">
      {/* Side Navigation */}
      <Sidebar
        mobileOpen={mobileSidebarOpen}
        onMobileClose={() => setMobileSidebarOpen(false)}
      />

      {/* Main System Viewport */}
      <div className="flex flex-1 flex-col min-w-0 h-full overflow-hidden">
        {/* Mobile-only Top Bar */}
        <header className="lg:hidden flex h-14 items-center justify-between px-4 bg-[#0B0F19] text-white shrink-0 border-b border-[#161F30] shadow-sm">
          <button
            type="button"
            onClick={() => setMobileSidebarOpen(true)}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-[#131B2E]"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold tracking-tight text-white">FormFlow</span>
            <span className="rounded bg-[#131B2E] border border-[#212E4A] px-1 py-0.2 font-mono text-[9px] font-bold text-[#A397F8]">
              SYSTEM
            </span>
          </div>
          <div className="w-7 h-7 rounded-full bg-[#6551f3] text-white text-xs font-bold flex items-center justify-center">
            {user.email.charAt(0).toUpperCase()}
          </div>
        </header>

        {/* Scrollable System Content Container */}
        <main className="flex-1 overflow-y-auto min-w-0 bg-[#f9f9fb]">
          {children}
        </main>
      </div>
    </div>
  );
}
