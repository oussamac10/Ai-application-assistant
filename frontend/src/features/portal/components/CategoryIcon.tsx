"use client";

import React from "react";
import {
  Home,
  Users,
  Briefcase,
  Globe,
  Car,
  HeartPulse,
  FileText,
  Sparkles,
  Layers,
  GraduationCap,
  Building2,
  Landmark,
  ShieldCheck,
} from "lucide-react";

interface CategoryIconProps {
  name?: string | null;
  icon?: string | null;
  className?: string;
}

export function CategoryIcon({ name, icon, className = "w-4 h-4" }: CategoryIconProps) {
  const normalized = (icon || name || "").toLowerCase().trim();

  switch (normalized) {
    case "home":
      return <Home className={className} />;
    case "users":
      return <Users className={className} />;
    case "briefcase":
      return <Briefcase className={className} />;
    case "globe":
      return <Globe className={className} />;
    case "car":
      return <Car className={className} />;
    case "heartpulse":
    case "heart":
      return <HeartPulse className={className} />;
    case "graduationcap":
    case "education":
      return <GraduationCap className={className} />;
    case "building2":
    case "building":
      return <Building2 className={className} />;
    case "landmark":
      return <Landmark className={className} />;
    case "shieldcheck":
    case "shield":
      return <ShieldCheck className={className} />;
    case "filetext":
    case "file":
      return <FileText className={className} />;
    case "sparkles":
      return <Sparkles className={className} />;
    default:
      return <Layers className={className} />;
  }
}
