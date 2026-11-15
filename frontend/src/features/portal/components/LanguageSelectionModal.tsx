"use client";

import React, { useMemo, useState } from "react";
import { Check, CheckCircle2, Globe, Search, X } from "lucide-react";

export interface GuidanceLanguage {
  code: string;
  name: string;
  native: string;
  region: "europe" | "mena" | "asia" | "africa";
}

export const COMPREHENSIVE_GUIDANCE_LANGUAGES: GuidanceLanguage[] = [
  // Europe
  { code: "de", name: "German", native: "Deutsch", region: "europe" },
  { code: "en", name: "English", native: "English", region: "europe" },
  { code: "fr", name: "French", native: "Français", region: "europe" },
  { code: "es", name: "Spanish", native: "Español", region: "europe" },
  { code: "it", name: "Italian", native: "Italiano", region: "europe" },
  { code: "pt", name: "Portuguese", native: "Português", region: "europe" },
  { code: "nl", name: "Dutch", native: "Nederlands", region: "europe" },
  { code: "pl", name: "Polish", native: "Polski", region: "europe" },
  { code: "ro", name: "Romanian", native: "Română", region: "europe" },
  { code: "el", name: "Greek", native: "Ελληνικά", region: "europe" },
  { code: "hu", name: "Hungarian", native: "Magyar", region: "europe" },
  { code: "cs", name: "Czech", native: "Čeština", region: "europe" },
  { code: "sk", name: "Slovak", native: "Slovenčina", region: "europe" },
  { code: "bg", name: "Bulgarian", native: "Български", region: "europe" },
  { code: "hr", name: "Croatian", native: "Hrvatski", region: "europe" },
  { code: "sr", name: "Serbian", native: "Srpski", region: "europe" },
  { code: "sv", name: "Swedish", native: "Svenska", region: "europe" },
  { code: "da", name: "Danish", native: "Dansk", region: "europe" },
  { code: "fi", name: "Finnish", native: "Suomi", region: "europe" },
  { code: "no", name: "Norwegian", native: "Norsk", region: "europe" },
  { code: "sq", name: "Albanian", native: "Shqip", region: "europe" },
  { code: "uk", name: "Ukrainian", native: "Українська", region: "europe" },
  { code: "ru", name: "Russian", native: "Русский", region: "europe" },
  { code: "ka", name: "Georgian", native: "ქართული", region: "europe" },
  { code: "hy", name: "Armenian", native: "Հայերեն", region: "europe" },

  // Middle East & North Africa (MENA)
  { code: "tr", name: "Turkish", native: "Türkçe", region: "mena" },
  { code: "ar", name: "Arabic", native: "العربية", region: "mena" },
  { code: "fa", name: "Persian (Farsi)", native: "فارسی", region: "mena" },
  { code: "ku", name: "Kurdish", native: "Kurdî / کوردی", region: "mena" },
  { code: "ps", name: "Pashto", native: "پښتو", region: "mena" },
  { code: "prs", name: "Dari", native: "دری", region: "mena" },
  { code: "he", name: "Hebrew", native: "עברית", region: "mena" },

  // South & East Asia
  { code: "hi", name: "Hindi", native: "हिन्दी", region: "asia" },
  { code: "ur", name: "Urdu", native: "اردو", region: "asia" },
  { code: "bn", name: "Bengali", native: "বাংলা", region: "asia" },
  { code: "pa", name: "Punjabi", native: "ਪੰਜਾਬੀ", region: "asia" },
  { code: "ta", name: "Tamil", native: "தமிழ்", region: "asia" },
  { code: "te", name: "Telugu", native: "తెలుగు", region: "asia" },
  { code: "zh", name: "Chinese (Simplified)", native: "简体中文", region: "asia" },
  { code: "zh-TW", name: "Chinese (Traditional)", native: "繁體中文", region: "asia" },
  { code: "ja", name: "Japanese", native: "日本語", region: "asia" },
  { code: "ko", name: "Korean", native: "한국어", region: "asia" },
  { code: "vi", name: "Vietnamese", native: "Tiếng Việt", region: "asia" },
  { code: "tl", name: "Tagalog (Filipino)", native: "Wikang Tagalog", region: "asia" },
  { code: "th", name: "Thai", native: "ไทย", region: "asia" },
  { code: "id", name: "Indonesian", native: "Bahasa Indonesia", region: "asia" },

  // Africa
  { code: "so", name: "Somali", native: "Soomaali", region: "africa" },
  { code: "ti", name: "Tigrinya", native: "ትግርኛ", region: "africa" },
  { code: "am", name: "Amharic", native: "አማርኛ", region: "africa" },
  { code: "sw", name: "Swahili", native: "Kiswahili", region: "africa" },
  { code: "yo", name: "Yoruba", native: "Èdè Yorùbá", region: "africa" },
  { code: "om", name: "Oromo", native: "Afaan Oromoo", region: "africa" },
];

export const LANGUAGE_MAP = new Map<string, GuidanceLanguage>(
  COMPREHENSIVE_GUIDANCE_LANGUAGES.map((l) => [l.code, l])
);

interface Props {
  isOpen: boolean;
  onClose: () => void;
  selectedLanguages: string[];
  onApply: (languages: string[]) => void;
}

export function LanguageSelectionModal({
  isOpen,
  onClose,
  selectedLanguages,
  onApply,
}: Props) {
  const [selected, setSelected] = useState<string[]>(selectedLanguages);
  const [search, setSearch] = useState("");
  const [regionFilter, setRegionFilter] = useState<string>("all");

  // Keep local selection in sync when reopened
  React.useEffect(() => {
    if (isOpen) {
      setSelected(selectedLanguages);
      setSearch("");
      setRegionFilter("all");
    }
  }, [isOpen, selectedLanguages]);

  const filteredLanguages = useMemo(() => {
    const q = search.trim().toLowerCase();
    return COMPREHENSIVE_GUIDANCE_LANGUAGES.filter((lang) => {
      if (regionFilter !== "all" && lang.region !== regionFilter) {
        return false;
      }
      if (!q) return true;
      return (
        lang.code.toLowerCase().includes(q) ||
        lang.name.toLowerCase().includes(q) ||
        lang.native.toLowerCase().includes(q)
      );
    });
  }, [search, regionFilter]);

  if (!isOpen) return null;

  const toggleLang = (code: string) => {
    if (selected.includes(code)) {
      if (selected.length > 1) {
        setSelected(selected.filter((c) => c !== code));
      }
    } else {
      setSelected([...selected, code]);
    }
  };

  const selectCoreEight = () => {
    const core = ["de", "en", "ar", "fr", "tr", "uk", "es", "ru"];
    setSelected(Array.from(new Set([...selected, ...core])));
  };

  const handleApply = () => {
    onApply(selected.length > 0 ? selected : ["de", "en"]);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#060910]/80 p-4 backdrop-blur-xs">
      <div className="surface-panel w-full max-w-3xl max-h-[90vh] flex flex-col rounded-2xl bg-[#0F1522] shadow-2xl border border-white/10 text-slate-100 overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-white/10 flex items-center justify-between bg-[#0A0E17]/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <Globe className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Choose Supported Guidance Languages
              </h3>
              <p className="text-xs text-slate-400">
                Select which native languages citizens can choose when filling your organization&apos;s forms.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-[#151D2E] hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search & Region Filter Bar */}
        <div className="p-4 border-b border-white/[0.08] space-y-3 bg-[#0F1522]">
          <div className="flex flex-col sm:flex-row gap-2.5 items-center justify-between">
            <div className="relative w-full sm:w-80">
              <div className="pointer-events-none absolute inset-y-0 start-0 flex items-center ps-3 text-slate-500">
                <Search className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by language, native name, code..."
                className="w-full rounded-xl border border-white/10 bg-[#0A0E17] py-2 ps-9 pe-3 text-xs text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>

            <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
              {[
                { id: "all", label: "All Regions" },
                { id: "europe", label: "Europe" },
                { id: "mena", label: "Middle East" },
                { id: "asia", label: "Asia" },
                { id: "africa", label: "Africa" },
              ].map((tab) => (
                <button
                  type="button"
                  key={tab.id}
                  onClick={() => setRegionFilter(tab.id)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-all cursor-pointer ${
                    regionFilter === tab.id
                      ? "bg-emerald-500 text-slate-950 font-bold shadow-2xs"
                      : "bg-[#0A0E17] border border-white/10 text-slate-300 hover:bg-[#151D2E] hover:text-white"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between text-xs pt-1">
            <span className="font-semibold text-slate-300">
              <span className="text-emerald-400 font-bold">{selected.length}</span> languages active for citizens
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={selectCoreEight}
                className="text-xs text-emerald-400 hover:text-emerald-300 font-medium underline cursor-pointer"
              >
                + Add Top 8 European Migrant Languages
              </button>
            </div>
          </div>
        </div>

        {/* Language Grid */}
        <div className="flex-1 overflow-y-auto p-4 max-h-[50vh]">
          {filteredLanguages.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400">
              No languages match your search query.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {filteredLanguages.map((lang) => {
                const isSelected = selected.includes(lang.code);
                return (
                  <button
                    type="button"
                    key={lang.code}
                    onClick={() => toggleLang(lang.code)}
                    className={`flex items-center justify-between p-3 rounded-xl border text-start transition-all cursor-pointer ${
                      isSelected
                        ? "border-emerald-500/60 bg-emerald-500/10 shadow-2xs ring-1 ring-emerald-500/30"
                        : "border-white/10 bg-[#0A0E17] hover:border-white/20 hover:bg-[#151D2E]"
                    }`}
                  >
                    <div className="flex flex-col">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-xs text-white">{lang.native}</span>
                        <span className="font-mono text-[10px] text-slate-400 bg-[#151D2E] border border-white/10 px-1.5 py-0.2 rounded uppercase">
                          {lang.code}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-400">{lang.name}</span>
                    </div>

                    <div
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-lg border transition-colors ${
                        isSelected
                          ? "border-emerald-500 bg-emerald-500 text-slate-950"
                          : "border-white/20 bg-[#0F1522]"
                      }`}
                    >
                      {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-white/10 flex items-center justify-between bg-[#0A0E17]/60">
          <span className="text-xs text-slate-400">
            Selected languages will be available in the citizen intake language picker.
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary px-4 py-2 text-xs font-medium"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleApply}
              className="btn-primary px-5 py-2 text-xs font-bold"
            >
              Apply Selection ({selected.length})
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
