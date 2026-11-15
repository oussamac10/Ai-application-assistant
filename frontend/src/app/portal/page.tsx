"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/context/AuthProvider";
import { PortalDashboard } from "@/features/portal/components/PortalDashboard";

export default function PortalPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login?redirect=/portal");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-[70vh] bg-[#0A0E17] text-slate-100 flex flex-col items-center justify-center p-4">
        <div className="w-10 h-10 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Loading Workspace...
        </p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return <PortalDashboard />;
}
