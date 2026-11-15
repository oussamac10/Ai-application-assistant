"use client";

import React from "react";
import { Moon, Sun } from "lucide-react";
import { useTranslations } from "next-intl";
import { useTheme } from "@/components/ThemeProvider";

interface ThemeToggleProps {
  variant?: "icon" | "pill";
  className?: string;
}

/** Accessible Dark/Light theme switcher control for Navbar and Sidebar surfaces. */
export default function ThemeToggle({
  variant = "icon",
  className = "",
}: ThemeToggleProps) {
  const { theme, setTheme, toggleTheme } = useTheme();
  const tNav = useTranslations("nav");

  const nextActionLabel =
    theme === "dark" ? tNav("switchToLight") : tNav("switchToDark");

  if (variant === "pill") {
    return (
      <div
        role="group"
        aria-label={nextActionLabel}
        className={`grid grid-cols-2 gap-1 rounded-xl border border-white/[0.1] bg-[#0A0E17] p-1 ${className}`.trim()}
      >
        <button
          type="button"
          onClick={() => setTheme("dark")}
          aria-pressed={theme === "dark"}
          className={`flex items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs transition-colors cursor-pointer ${
            theme === "dark"
              ? "bg-emerald-500 text-slate-950 font-bold shadow-2xs"
              : "text-slate-400 hover:text-white font-medium"
          }`}
        >
          <Moon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>{tNav("themeDark")}</span>
        </button>
        <button
          type="button"
          onClick={() => setTheme("light")}
          aria-pressed={theme === "light"}
          className={`flex items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs transition-colors cursor-pointer ${
            theme === "light"
              ? "bg-emerald-500 text-slate-950 font-bold shadow-2xs"
              : "text-slate-400 hover:text-white font-medium"
          }`}
        >
          <Sun className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span>{tNav("themeLight")}</span>
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={nextActionLabel}
      title={nextActionLabel}
      className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/[0.12] bg-[#0F1522] text-slate-200 shadow-2xs transition-colors hover:border-emerald-500/40 hover:bg-[#151D2E] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 cursor-pointer ${className}`.trim()}
    >
      {theme === "dark" ? (
        <Sun className="h-4 w-4 text-amber-400" aria-hidden="true" />
      ) : (
        <Moon className="h-4 w-4 text-emerald-400" aria-hidden="true" />
      )}
    </button>
  );
}
