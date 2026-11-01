"use client";

import React from "react";
import { useParams } from "next/navigation";
import { CandidateIntakeLanding } from "@/features/portal/components/CandidateIntakeLanding";

export default function CandidateInvitePage() {
  const params = useParams();
  const token = typeof params?.token === "string" ? params.token : "";

  if (!token) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center p-4">
        <p className="text-xs text-slate-500">Invalid invite link parameter.</p>
      </div>
    );
  }

  return <CandidateIntakeLanding token={token} />;
}
