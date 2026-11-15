"use client";

import React, { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getPublishedForms, PublishedForm } from "@/features/form-session/services/apiClient";
import { UNIVERSAL_LANGUAGES } from "@/features/form-session/utils/languages";
import { ModernSelect } from "@/components/ui/ModernSelect";
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
    return { code: "GOV", label: "Official Government Authority", outputLang: "Official Destination Language" };
  }
  const key = (template.templateKey || "").toLowerCase();
  const name = (template.name || "").toLowerCase();
  if (key.startsWith("eu-") || name.includes("schengen") || name.includes("eu ")) {
    return { code: "EU", label: "European Union (Schengen Area)", outputLang: "English / Harmonised EU" };
  }
  if (key.startsWith("us-") || name.includes("united states") || name.includes("uscis")) {
    return { code: "US", label: "United States (Federal / USCIS / IRS)", outputLang: "English (US Official)" };
  }
  if (key.startsWith("uk-") || name.includes("united kingdom") || name.includes("home office")) {
    return { code: "UK", label: "United Kingdom (Home Office / HMRC)", outputLang: "English (UK Official)" };
  }
  if (key.startsWith("ca-") || name.includes("canada") || name.includes("ircc")) {
    return { code: "CA", label: "Canada (IRCC / CRA)", outputLang: "English / French" };
  }
  if (key.startsWith("de-") || name.includes("deutschland") || name.includes("bundes") || name.includes("aufenthalt")) {
    return { code: "DE", label: "Germany (Federal / State Authority)", outputLang: "German (Official)" };
  }
  if (key.startsWith("fr-") || name.includes("france")) {
    return { code: "FR", label: "France (Préfecture / Ministère)", outputLang: "French (Official)" };
  }
  return { code: "GOV", label: "Official Destination Authority", outputLang: "Official Destination Language" };
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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#060910]/80 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div className="relative w-full max-w-xl rounded-2xl bg-[#0F1522] border border-white/10 text-slate-100 p-6 shadow-2xl sm:p-8">
        <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
          <div>
            <h2 id="modal-headline" className="text-xl font-bold text-white">
              {t("modalTitle")}
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Invite a citizen or applicant to complete an official administrative form in their native language.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-[#151D2E] hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs text-rose-200">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-1.5">
              {t("candidateNameLabel")} *
            </label>
            <input
              type="text"
              required
              value={candidateName}
              onChange={(e) => setCandidateName(e.target.value)}
              placeholder={t("candidateNamePlaceholder")}
              className="w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-1.5">
              {t("candidateEmailLabel")} *
            </label>
            <input
              type="email"
              required
              value={candidateEmail}
              onChange={(e) => setCandidateEmail(e.target.value)}
              placeholder={t("candidateEmailPlaceholder")}
              className="w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-1.5">
              {t("formLabel")} *
            </label>
            {loadingTemplates ? (
              <div className="py-2.5 text-xs text-slate-400 animate-pulse">
                Loading official templates...
              </div>
            ) : (
              <ModernSelect
                value={selectedFormId}
                onChange={(val) => setSelectedFormId(val)}
                options={templates.map((tmpl) => ({
                  value: tmpl.id,
                  label: tmpl.name,
                }))}
                placeholder="Select official template..."
                searchable={templates.length > 5}
                searchPlaceholder="Search forms..."
                aria-label="Official Template"
              />
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-1.5">
                {t("languageLabel")}
              </label>
              <ModernSelect
                value={userLanguage}
                onChange={(val) => setUserLanguage(val)}
                options={UNIVERSAL_LANGUAGES.map((lang) => ({
                  value: lang.code,
                  label: `${lang.nativeName} (${lang.englishName})`,
                }))}
                searchable
                searchPlaceholder="Search languages..."
                aria-label="Assistance Language"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-1.5">
                Destination Jurisdiction
              </label>
              {(() => {
                const selected = templates.find((t) => t.id === selectedFormId);
                const info = getJurisdictionInfo(selected);
                return (
                  <div className="flex items-center gap-2 h-10 px-3.5 rounded-xl border border-white/10 bg-[#0A0E17] text-xs font-medium text-slate-200">
                    <span className="font-mono font-bold text-[10px] uppercase tracking-wider rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 text-emerald-400">
                      {info.code}
                    </span>
                    <span className="truncate">{info.label}</span>
                  </div>
                );
              })()}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-1.5">
              {t("notesLabel")}
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={t("notesPlaceholder")}
              className="w-full rounded-xl border border-white/10 bg-[#0A0E17] px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/[0.08]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-[#151D2E] rounded-xl transition-colors cursor-pointer"
            >
              {t("cancel")}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-2.5 text-xs font-bold text-slate-950 shadow-xs hover:bg-emerald-400 disabled:opacity-50 transition-colors cursor-pointer"
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
