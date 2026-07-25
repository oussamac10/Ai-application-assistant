"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import { getPublishedForms, createSession, PublishedForm } from "@/features/form-session/services/apiClient";
import { setSessionToken } from "@/features/form-session/services/sessionCredentials";

export default function ApplicationLanding() {
  const router = useRouter();
  const t = useTranslations("landing");
  const tc = useTranslations("common");
  const te = useTranslations("errors");
  const { locale, setLocale } = useLanguage();

  const [forms, setForms] = useState<PublishedForm[]>([]);
  const [selectedFormId, setSelectedFormId] = useState<string>("");
  const [outputLanguage, setOutputLanguage] = useState<string>("en");
  const [privacyAccepted, setPrivacyAccepted] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadForms() {
      try {
        setErrorMsg(null);
        const data = await getPublishedForms();
        setForms(data);
        if (data.length > 0) {
          setSelectedFormId(data[0].id);
        }
      } catch (err: any) {
        setErrorMsg(te(err.message) || "Failed to load forms list. Please retry.");
      } finally {
        setLoading(false);
      }
    }
    loadForms();
  }, [te]);

  const selectedForm = forms.find((f) => f.id === selectedFormId);

  useEffect(() => {
    if (selectedForm) {
      // Reset outputLanguage to first supported option when form changes
      if (!selectedForm.supportedOutputLanguages.includes(outputLanguage)) {
        setOutputLanguage(selectedForm.supportedOutputLanguages[0] || "en");
      }
    }
  }, [selectedForm, outputLanguage]);

  const handleStartSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFormId || !privacyAccepted || submitting) return;

    try {
      setSubmitting(true);
      setErrorMsg(null);

      // Create anonymous session
      const session = await createSession(selectedFormId, locale, outputLanguage);

      if (session.ownershipToken) {
        setSessionToken(session.publicId, session.ownershipToken);
      }

      router.push(`/application/session/${session.publicId}`);
    } catch (err: any) {
      setErrorMsg(te(err.message) || "An unexpected error occurred. Please try again.");
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 text-slate-100">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-700 border-t-indigo-500" />
          <p className="text-sm font-medium text-slate-400">{tc("loading")}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-tr from-slate-950 via-slate-900 to-indigo-950 px-4 py-12 text-slate-100 sm:px-6 lg:px-8">
      <div className="w-full max-w-xl">
        <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-900/60 p-6 md:p-8 shadow-2xl backdrop-blur-xl">
          {/* Decorative glowing gradient spheres */}
          <div className="absolute -right-20 -top-20 h-40 w-40 rounded-full bg-indigo-500/10 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 h-40 w-40 rounded-full bg-violet-500/10 blur-3xl" />

          <div className="relative z-10">
            <h1 className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-3xl font-extrabold tracking-tight text-transparent text-center">
              {tc("title")}
            </h1>
            <p className="mt-2 text-center text-sm text-slate-400">
              Select languages and form options to begin
            </p>

            <form onSubmit={handleStartSession} className="mt-8 space-y-6">
              {errorMsg && (
                <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-4 text-sm text-rose-300">
                  {errorMsg}
                </div>
              )}

              {/* 1. UI Language Selection */}
              <div className="space-y-2">
                <label className="block text-sm font-semibold tracking-wide text-slate-300">
                  {t("selectUiLanguage")}
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { code: "en", label: "English" },
                    { code: "de", label: "Deutsch" },
                    { code: "fr", label: "Français" },
                    { code: "ar", label: "العربية" },
                  ].map((lang) => (
                    <button
                      key={lang.code}
                      type="button"
                      className={`rounded-xl border py-2.5 text-sm font-semibold transition ${
                        locale === lang.code
                          ? "border-indigo-500 bg-indigo-500/10 text-indigo-400"
                          : "border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700 hover:text-slate-300"
                      }`}
                      onClick={() => setLocale(lang.code)}
                    >
                      {lang.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 2. Form Selection */}
              <div className="space-y-2">
                <label htmlFor="form-select" className="block text-sm font-semibold tracking-wide text-slate-300">
                  {t("selectForm")}
                </label>
                {forms.length === 0 ? (
                  <div className="rounded-xl border border-slate-800 bg-slate-950/20 p-4 text-center text-sm text-slate-500">
                    No forms currently available.
                  </div>
                ) : (
                  <select
                    id="form-select"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3.5 text-base text-slate-100 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 appearance-none cursor-pointer"
                    value={selectedFormId}
                    onChange={(e) => setSelectedFormId(e.target.value)}
                  >
                    {forms.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name} (v{f.versionNumber})
                      </option>
                    ))}
                  </select>
                )}
                {selectedForm?.description && (
                  <p className="text-xs text-slate-400 italic px-1">
                    {selectedForm.description}
                  </p>
                )}
              </div>

              {/* 3. Output Language Selection */}
              {selectedForm && (
                <div className="space-y-2">
                  <label htmlFor="output-select" className="block text-sm font-semibold tracking-wide text-slate-300">
                    {t("selectOutputLanguage")}
                  </label>
                  <select
                    id="output-select"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3.5 text-base text-slate-100 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 appearance-none cursor-pointer"
                    value={outputLanguage}
                    onChange={(e) => setOutputLanguage(e.target.value)}
                  >
                    {selectedForm.supportedOutputLanguages.map((lang) => (
                      <option key={lang} value={lang}>
                        {lang === "en" ? "English" : lang === "de" ? "Deutsch" : lang === "fr" ? "Français" : lang === "ar" ? "العربية" : lang.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* 4. Privacy Notice */}
              <div className="space-y-3 rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
                <h3 className="text-sm font-bold text-slate-200">{t("privacyNoticeTitle")}</h3>
                <p className="text-xs leading-relaxed text-slate-400">{t("privacyNoticeBody")}</p>
                <label className="flex items-center gap-3 cursor-pointer select-none text-slate-300">
                  <input
                    type="checkbox"
                    className="h-5 w-5 rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500/20 cursor-pointer"
                    checked={privacyAccepted}
                    onChange={(e) => setPrivacyAccepted(e.target.checked)}
                  />
                  <span className="text-xs font-semibold">{t("acceptPrivacy")}</span>
                </label>
              </div>

              {/* 5. Submit Button */}
              <button
                type="submit"
                disabled={!privacyAccepted || submitting || forms.length === 0}
                className="relative w-full overflow-hidden rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 py-4 text-base font-bold shadow-lg shadow-indigo-500/20 transition hover:opacity-95 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 disabled:opacity-40 disabled:pointer-events-none active:scale-[0.99]"
              >
                {submitting ? (
                  <div className="flex items-center justify-center gap-2">
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                    <span>{tc("loading")}</span>
                  </div>
                ) : (
                  <span>{t("startSession")}</span>
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </main>
  );
}
