"use client";

import React from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ShieldCheck, Lock, Server, CheckCircle2 } from "lucide-react";

export default function Footer() {
  const t = useTranslations("footer");
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-white/[0.08] bg-[#080C14] text-slate-400">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8 space-y-8">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-md space-y-3">
            <div className="flex items-center gap-2.5">
              <span className="text-base font-bold tracking-tight text-white">
                FormFlow
              </span>
              <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-emerald-400">
                GLOBAL INFRASTRUCTURE
              </span>
            </div>
            <p className="text-xs leading-relaxed text-slate-400">
              {t("tagline")}
            </p>

            {/* Technical Security & Compliance Badges */}
            <div className="flex flex-wrap items-center gap-2 pt-1 font-mono text-[10px]">
              <span className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.08] bg-[#0F1522] px-2 py-1 text-slate-300">
                <ShieldCheck className="h-3 w-3 text-emerald-400" />
                <span>GDPR ART. 17/20</span>
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.08] bg-[#0F1522] px-2 py-1 text-slate-300">
                <Lock className="h-3 w-3 text-emerald-400" />
                <span>AES-256 FERNET</span>
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.08] bg-[#0F1522] px-2 py-1 text-slate-300">
                <Server className="h-3 w-3 text-emerald-400" />
                <span>EU SOVEREIGN HOSTING</span>
              </span>
            </div>
          </div>

          <div className="space-y-3 lg:text-end">
            {/* System Status Indicator */}
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 font-mono text-xs text-emerald-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>SYSTEM OPERATIONAL • 0% AI HALLUCINATION</span>
            </div>

            <nav
              aria-label="Footer navigation"
              className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs font-medium lg:justify-end"
            >
              <Link
                href="/application"
                className="text-slate-400 transition-colors hover:text-emerald-400"
              >
                {t("startForm")}
              </Link>
              <Link
                href="/account"
                className="text-slate-400 transition-colors hover:text-emerald-400"
              >
                {t("accountPrivacy")}
              </Link>
              <Link
                href="/impressum"
                className="text-slate-400 transition-colors hover:text-emerald-400"
              >
                {t("impressum")}
              </Link>
              <Link
                href="/datenschutz"
                className="text-slate-400 transition-colors hover:text-emerald-400"
              >
                {t("datenschutz")}
              </Link>
              <Link
                href="/agb"
                className="text-slate-400 transition-colors hover:text-emerald-400"
              >
                {t("agb")}
              </Link>
            </nav>
          </div>
        </div>

        <div className="border-t border-white/[0.06] pt-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between text-start">
          <p className="max-w-3xl text-[11px] leading-relaxed text-slate-500">
            {t("rdgDisclaimer")}
          </p>
          <span className="shrink-0 font-mono text-[11px] text-slate-500 tabular-nums">
            <bdi>© {currentYear} FormFlow • Universal Form Assistant</bdi>
          </span>
        </div>
      </div>
    </footer>
  );
}
