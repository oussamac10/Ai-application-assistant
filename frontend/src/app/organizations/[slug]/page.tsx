import React from "react";
import { Metadata } from "next";
import { PublicOrganizationPortal } from "@/features/portal/components/PublicOrganizationPortal";

interface Props {
  params: Promise<{ slug: string }> | { slug: string };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const resolvedParams = await params;
  const slug = resolvedParams.slug;
  const formatted = slug
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

  return {
    title: `${formatted} — Official Form Portal | AI Form Assistant`,
    description: `Official administrative and citizen form portal for ${formatted}. Complete official documents in your native language for free.`,
  };
}

export default async function OrganizationPortalPage({ params }: Props) {
  const resolvedParams = await params;
  return <PublicOrganizationPortal slug={resolvedParams.slug} />;
}
