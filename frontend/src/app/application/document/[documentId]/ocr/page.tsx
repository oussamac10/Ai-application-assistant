"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import OcrPanel from "@/features/document-ocr/components/OcrPanel";

export default function DocumentOcrPage() {
  const params = useParams<{ documentId: string }>();
  const tc = useTranslations("common");
  const { locale } = useLanguage();

  return (
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center bg-[#0A0E17] px-4 py-12 text-slate-100 sm:px-6 lg:px-8">
      <div className="w-full max-w-xl">
        <div className="surface-panel relative overflow-hidden rounded-2xl p-6 md:p-8">
          <div className="pointer-events-none absolute -right-20 -top-20 h-40 w-40 rounded-full bg-emerald-500/10 blur-3xl" />

          <div className="relative z-10">
            <h1 className="text-2xl font-bold tracking-tight text-white text-center">
              {tc("title")}
            </h1>
            <div className="mt-6">
              <OcrPanel documentId={params.documentId} currentLocale={locale} />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
