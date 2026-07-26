"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import FieldDetectionPanel from "@/features/field-detection/components/FieldDetectionPanel";

export default function DocumentFieldDetectionPage() {
  const params = useParams<{ documentId: string }>();
  const tc = useTranslations("common");
  const { locale } = useLanguage();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 px-4 py-12 text-slate-100 sm:px-6 lg:px-8">
      <div className="w-full max-w-xl">
        <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/60 p-6 md:p-8 shadow-2xl backdrop-blur-xl">
          <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-indigo-500/10 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 h-40 w-40 rounded-full bg-violet-500/10 blur-3xl" />

          <div className="relative z-10">
            <h1 className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-2xl font-extrabold tracking-tight text-transparent text-center">
              {tc("title")}
            </h1>
            <div className="mt-6">
              <FieldDetectionPanel documentId={params.documentId} currentLocale={locale} />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
