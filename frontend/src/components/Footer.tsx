"use client";

import React from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";

export default function Footer() {
  const t = useTranslations("footer");
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-slate-200 bg-white text-slate-600">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8 space-y-5">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-md space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-tight text-slate-900">
                FormFlow
              </span>
              <span className="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[10px] font-medium text-slate-600">
                EU • GDPR
              </span>
            </div>
            <p className="text-xs leading-relaxed text-slate-600">
              {t("tagline")}
            </p>
          </div>

          <nav
            aria-label="Footer navigation"
            className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-medium"
          >
            <Link
              href="/application"
              className="text-slate-600 transition-colors hover:text-indigo-700"
            >
              {t("startForm")}
            </Link>
            <Link
              href="/account"
              className="text-slate-600 transition-colors hover:text-indigo-700"
            >
              {t("accountPrivacy")}
            </Link>
            <Link
              href="/impressum"
              className="text-slate-600 transition-colors hover:text-indigo-700"
            >
              {t("impressum")}
            </Link>
            <Link
              href="/datenschutz"
              className="text-slate-600 transition-colors hover:text-indigo-700"
            >
              {t("datenschutz")}
            </Link>
            <Link
              href="/agb"
              className="text-slate-600 transition-colors hover:text-indigo-700"
            >
              {t("agb")}
            </Link>
          </nav>
        </div>

        <div className="border-t border-slate-100 pt-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <p className="max-w-3xl text-[11px] leading-relaxed text-slate-500">
            {t("rdgDisclaimer")}
          </p>
          <span className="shrink-0 font-mono text-[11px] text-slate-400 tabular-nums">
            <bdi>© {currentYear} FormFlow</bdi>
          </span>
        </div>
      </div>
    </footer>
  );
}
