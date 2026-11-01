import React from "react";
import { Metadata } from "next";
import { CitizenDirectory } from "@/features/portal/components/CitizenDirectory";

export const metadata: Metadata = {
  title: "Official Municipal Portals & Authorities | AI Form Assistant",
  description:
    "Find your city administration, Bürgeramt, or immigration authority to complete official administrative forms in your native language for free.",
};

export default function OrganizationsDirectoryPage() {
  return <CitizenDirectory />;
}
