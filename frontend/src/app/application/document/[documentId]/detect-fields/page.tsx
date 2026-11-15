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
    <main className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center bg-[#0A0E17] px-4 py-10 text-slate-100 sm:px-6 lg:px-8">
      <div className="w-full max-w-xl">
        <div className="surface-panel rounded-2xl p-6 sm:p-8">
          <h1 className="text-2xl font-bold tracking-tight text-white text-center">
            {tc("title")}
          </h1>
          <div className="mt-6">
            <FieldDetectionPanel documentId={params.documentId} currentLocale={locale} />
          </div>
        </div>
      </div>
    </main>
  );
}
