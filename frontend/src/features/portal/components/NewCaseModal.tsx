"use client";

import React, { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getPublishedForms, PublishedForm } from "@/features/form-session/services/apiClient";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import { createCase } from "../services/portalClient";
import { Case } from "../types";
import { X, Loader2 } from "lucide-react";

interface NewCaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCaseCreated: (newCase: Case) => void;
}

function getJurisdictionInfo(template?: PublishedForm) {
  if (!template) {
    return { flag: "🌐", label: "Official Government Authority", outputLang: "Official Destination Language" };
  }
  const key = (template.templateKey || "").toLowerCase();
  const name = (template.name || "").toLowerCase();
  if (key.startsWith("eu-") || name.includes("schengen") || name.includes("eu ")) {
    return { flag: "🇪🇺", label: "European Union (Schengen Area)", outputLang: "English / Harmonised EU" };
  }
  if (key.startsWith("us-") || name.includes("united states") || name.includes("uscis")) {
    return { flag: "🇺🇸", label: "United States (Federal / USCIS / IRS)", outputLang: "English (US Official)" };
  }
  if (key.startsWith("uk-") || name.includes("united kingdom") || name.includes("home office")) {
    return { flag: "🇬🇧", label: "United Kingdom (Home Office / HMRC)", outputLang: "English (UK Official)" };
  }
  if (key.startsWith("ca-") || name.includes("canada") || name.includes("ircc")) {
    return { flag: "🇨🇦", label: "Canada (IRCC / CRA)", outputLang: "English / French" };
  }
  if (key.startsWith("de-") || name.includes("deutschland") || name.includes("bundes") || name.includes("aufenthalt")) {
    return { flag: "🇩🇪", label: "Germany (Federal / State Authority)", outputLang: "German (Official)" };
  }
  if (key.startsWith("fr-") || name.includes("france")) {
    return { flag: "🇫🇷", label: "France (Préfecture / Ministère)", outputLang: "French (Official)" };
  }
  return { flag: "🌐", label: "Official Destination Authority", outputLang: "Official Destination Language" };
}

export function NewCaseModal({
  isOpen,
  onClose,
  onCaseCreated,
}: NewCaseModalProps) {
  const t = useTranslations("portal");
  const [candidateName, setCandidateName] = useState("");
  const [candidateEmail, setCandidateEmail] = useState("");
  const [selectedFormId, setSelectedFormId] = useState("");
  const [userLanguage, setUserLanguage] = useState("en");
  const [notes, setNotes] = useState("");
  const [templates, setTemplates] = useState<PublishedForm[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setLoadingTemplates(true);
    getPublishedForms()
      .then((forms) => {
        const officialForms = forms.filter(
          (f) =>
            !f.name?.toLowerCase().includes("signature demo") &&
            !f.name?.toLowerCase().includes("development")
        );
        setTemplates(officialForms);
        if (officialForms.length > 0) {
          // Default to residence permit / aufenthaltstitel if present, else first form
          const permit = officialForms.find(
            (f) =>
              f.name?.toLowerCase().includes("aufenthalt") ||
              f.templateKey?.toLowerCase().includes("aufenthalt")
          );
          setSelectedFormId(permit ? permit.id : officialForms[0].id);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch templates:", err);
      })
      .finally(() => setLoadingTemplates(false));
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!candidateName.trim() || !candidateEmail.trim() || !selectedFormId) {
      setError("Please fill in candidate name, email, and choose a form.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const created = await createCase({
        candidate_name: candidateName.trim(),
        candidate_email: candidateEmail.trim(),
        form_version_id: selectedFormId,
        user_language: userLanguage,
        notes: notes.trim() || undefined,
      });
      onCaseCreated(created);
      onClose();
      // Reset form
      setCandidateName("");
      setCandidateEmail("");
      setNotes("");
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to create candidate case."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-headline"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl ring-1 ring-slate-900/10 sm:p-8">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div>
            <h2 id="modal-headline" className="text-xl font-bold text-slate-900">
              {t("modalTitle")}
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Invite a citizen or applicant to complete an official administrative form in their native language.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-none"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              {t("candidateNameLabel")} *
            </label>
            <input
              type="text"
              required
              value={candidateName}
              onChange={(e) => setCandidateName(e.target.value)}
              placeholder={t("candidateNamePlaceholder")}
              className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/15"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              {t("candidateEmailLabel")} *
            </label>
            <input
              type="email"
              required
              value={candidateEmail}
              onChange={(e) => setCandidateEmail(e.target.value)}
              placeholder={t("candidateEmailPlaceholder")}
              className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/15"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              {t("formLabel")} *
            </label>
            {loadingTemplates ? (
              <div className="py-2.5 text-xs text-slate-500 animate-pulse">
                Loading official templates...
              </div>
            ) : (
              <select
                value={selectedFormId}
                onChange={(e) => setSelectedFormId(e.target.value)}
                required
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm text-slate-900 bg-white focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/15"
              >
                {templates.map((tmpl) => (
                  <option key={tmpl.id} value={tmpl.id}>
                    {tmpl.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                {t("languageLabel")}
              </label>
              <select
                value={userLanguage}
                onChange={(e) => setUserLanguage(e.target.value)}
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm text-slate-900 bg-white focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/15"
              >
                {UNIVERSAL_LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.nativeName} ({lang.englishName})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Destination Jurisdiction
              </label>
              {(() => {
                const selected = templates.find((t) => t.id === selectedFormId);
                const info = getJurisdictionInfo(selected);
                return (
                  <div className="flex items-center gap-2 h-10 px-3.5 rounded-xl border border-slate-200 bg-slate-50 text-xs font-medium text-slate-700">
                    <span className="text-base">{info.flag}</span>
                    <span className="truncate">{info.label}</span>
                  </div>
                );
              })()}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              {t("notesLabel")}
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={t("notesPlaceholder")}
              className="w-full rounded-xl border border-slate-200 px-3.5 py-2 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-600/15 resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              {t("cancel")}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  {t("creating")}
                </>
              ) : (
                t("createButton")
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
