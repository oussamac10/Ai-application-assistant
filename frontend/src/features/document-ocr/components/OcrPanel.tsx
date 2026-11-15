"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { requestOcr, getOcrResult } from "../services/apiClient";
import { OcrResultResponse } from "../types";
import { ApiError } from "../../form-session/services/apiClient";
import { Loader2 } from "lucide-react";

interface OcrPanelProps {
  documentId: string;
  currentLocale: string;
}

export default function OcrPanel({ documentId, currentLocale }: OcrPanelProps) {
  const router = useRouter();
  const t = useTranslations("documentOcr");

  const [language, setLanguage] = useState<string>(currentLocale);
  const [stage, setStage] = useState<"idle" | "processing" | "completed" | "failed">(
    "idle"
  );
  const [result, setResult] = useState<OcrResultResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activePage, setActivePage] = useState<number>(0);

  useEffect(() => {
    let cancelled = false;

    async function loadExisting() {
      try {
        const existing = await getOcrResult(documentId);
        if (cancelled) return;
        setResult(existing);
        setStage(existing.status === "completed" ? "completed" : "idle");
      } catch {
        // No prior OCR result yet; stay idle.
      }
    }

    loadExisting();
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  const handleRequestOcr = async () => {
    setStage("processing");
    setErrorMsg(null);
    try {
      const response = await requestOcr(documentId, language);
      setResult(response);
      setActivePage(0);
      setStage(response.status === "completed" ? "completed" : "failed");
    } catch (err: any) {
      setStage("failed");
      if (err instanceof ApiError) {
        const key = `error_${err.detail}`;
        const msg = t(key);
        setErrorMsg(msg && msg !== key ? msg : err.message || t("error_generic"));
      } else {
        setErrorMsg(err.message || t("error_generic"));
      }
    }
  };

  const page = result?.pages[activePage];

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-white/10 bg-[#0A0E17] p-6 space-y-4">
        <h2 className="text-xl font-bold text-white">{t("title")}</h2>
        <p className="text-xs leading-relaxed text-slate-400">{t("body")}</p>

        {stage !== "completed" && (
          <>
            <div className="space-y-2">
              <label
                htmlFor="ocr-language-select"
                className="block text-sm font-semibold tracking-wide text-slate-200"
              >
                {t("selectLanguage")}
              </label>
              <select
                id="ocr-language-select"
                className="w-full rounded-xl border border-white/10 bg-[#0F1522] px-4 py-3.5 text-base text-slate-100 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 cursor-pointer"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                disabled={stage === "processing"}
              >
                <option value="en" className="bg-[#0F1522] text-slate-100">English</option>
                <option value="de" className="bg-[#0F1522] text-slate-100">Deutsch</option>
                <option value="fr" className="bg-[#0F1522] text-slate-100">Français</option>
                <option value="ar" className="bg-[#0F1522] text-slate-100">العربية</option>
              </select>
            </div>

            <button
              type="button"
              disabled={stage === "processing"}
              onClick={handleRequestOcr}
              className="btn-primary w-full py-3.5 text-sm font-bold"
            >
              {stage === "processing" ? (
                <div className="flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{t("processing")}</span>
                </div>
              ) : (
                <span>{t("startOcr")}</span>
              )}
            </button>
          </>
        )}

        {stage === "failed" && errorMsg && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {errorMsg}
          </div>
        )}
      </div>

      {stage === "completed" && result && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-white/10 bg-[#0A0E17] p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white">{t("resultTitle")}</h3>
              <span className="text-xs text-slate-400">
                {t("pageCount", { count: result.pageCount ?? 0 })}
              </span>
            </div>

            {result.pages.length > 1 && (
              <div className="flex flex-wrap gap-2">
                {result.pages.map((p, index) => (
                  <button
                    key={p.pageNumber}
                    type="button"
                    onClick={() => setActivePage(index)}
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                      index === activePage
                        ? "bg-emerald-500 text-slate-950 font-bold"
                        : "border border-white/10 bg-[#151D2E] text-slate-300 hover:bg-[#1E293B] hover:text-white"
                    }`}
                  >
                    {t("page", { number: p.pageNumber })}
                  </button>
                ))}
              </div>
            )}

            {page && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>{t("confidence", { value: Math.round(page.averageConfidence) })}</span>
                </div>
                <p
                  dir="auto"
                  className="whitespace-pre-wrap rounded-xl border border-white/[0.08] bg-[#0F1522] p-4 text-sm leading-relaxed text-slate-200"
                >
                  {page.text || t("emptyPage")}
                </p>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => router.push(`/application/document/${documentId}/detect-fields`)}
            className="btn-primary w-full py-3.5 text-sm font-bold"
          >
            {t("detectFields")}
          </button>
        </div>
      )}
    </div>
  );
}
