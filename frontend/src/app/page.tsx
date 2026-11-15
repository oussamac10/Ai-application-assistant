"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useLanguage } from "@/features/form-session/components/LanguageProvider";
import {
  UNIVERSAL_LANGUAGES,
  getLanguageByCode,
} from "@/features/form-session/utils/languages";
import {
  PublishedForm,
  createSession,
  getPublishedForms,
} from "@/features/form-session/services/apiClient";
import { setSessionToken } from "@/features/form-session/services/sessionCredentials";
import {
  UploadCloud,
  Globe,
  ShieldCheck,
  CheckCircle2,
  FileText,
  Search,
  Lock,
  Zap,
  ArrowRight,
  Sparkles,
  Check,
  Languages,
} from "lucide-react";

const LAUNCH_UI_CODES = ["en", "de", "fr", "ar", "tr", "uk", "es", "ru"] as const;

interface ShowcaseDoc {
  id: string;
  tabLabel: string;
  title: string;
  regionLabel: string;
  stepTag: string;
  fieldBadge: string;
  fieldLabel: string;
  sampleValue: string;
  translations: Record<string, { question: string; explanation: string }>;
}

const SHOWCASE_DOCS: ShowcaseDoc[] = [
  {
    id: "visa",
    tabLabel: "Visa & Work",
    title: "Visa & Work Permit Form",
    regionLabel: "International",
    stepTag: "Question 1",
    fieldBadge: "Required",
    fieldLabel: "Full Legal Name (As Shown on Passport)",
    sampleValue: "Dr. Elena Rostova",
    translations: {
      en: {
        question: "What is your full legal name as shown on your passport?",
        explanation: "Enter your first name, middle names (if any), and family name in Roman letters exactly as they appear on your passport.",
      },
      ar: {
        question: "ما هو اسمك القانوني الكامل كما هو موضح في جواز السفر؟",
        explanation: "أدخل اسمك الأول والاسم الأوسط واسم العائلة بالأحرف اللاتينية تماماً كما تظهر في جواز سفرك.",
      },
      fr: {
        question: "Quel est votre nom légal complet tel qu'il figure sur votre passeport ?",
        explanation: "Indiquez votre prénom, vos éventuels autres prénoms et votre nom de famille en caractères latins, exactement tels qu'ils figurent sur votre passeport.",
      },
      de: {
        question: "Wie lautet Ihr vollständiger Name laut Reisepass?",
        explanation: "Geben Sie Vor- und Nachnamen exakt so ein, wie sie in Ihrem Reisepass stehen.",
      },
      es: {
        question: "¿Cuál es su nombre legal completo según figura en su pasaporte?",
        explanation: "Escriba su nombre y apellidos en alfabeto latino exactamente como aparecen en su pasaporte.",
      },
      tr: {
        question: "Pasaportunuzda görünen tam adınız nedir?",
        explanation: "Adınızı ve soyadınızı pasaportunuzda yer aldığı şekilde Latin harfleriyle girin.",
      },
    },
  },
  {
    id: "residence",
    tabLabel: "Address",
    title: "Address Registration Form",
    regionLabel: "Europe",
    stepTag: "Question 4",
    fieldBadge: "Date",
    fieldLabel: "Move-In Date",
    sampleValue: "01.03.2026",
    translations: {
      en: {
        question: "On what date did you move into this home?",
        explanation: "Enter the move-in date from your lease or landlord letter. We check the date format automatically.",
      },
      ar: {
        question: "في أي تاريخ انتقلت إلى هذا السكن؟",
        explanation: "أدخل تاريخ الانتقال المذكور في عقد الإيجار أو إفادة المالك، وسنضبط تنسيق التاريخ تلقائياً.",
      },
      fr: {
        question: "À quelle date avez-vous emménagé dans ce logement ?",
        explanation: "Indiquez la date d'emménagement figurant sur votre bail ou attestation. Le format de la date est vérifié automatiquement.",
      },
      de: {
        question: "Wann sind Sie in diese Wohnung eingezogen?",
        explanation: "Geben Sie das Einzugsdatum laut Mietvertrag oder Wohnungsgeberbestätigung an. Das Datumsformat wird automatisch geprüft.",
      },
      es: {
        question: "¿En qué fecha se mudó a esta vivienda?",
        explanation: "Indique la fecha de entrada que figura en su contrato o certificado. Comprobamos el formato automáticamente.",
      },
      tr: {
        question: "Bu adrese hangi tarihte taşındınız?",
        explanation: "Kira sözleşmenizde veya ev sahibi belgenizde yazan taşınma tarihini girin; tarih biçimi otomatik kontrol edilir.",
      },
    },
  },
  {
    id: "tax",
    tabLabel: "Tax ID",
    title: "Tax Registration Form",
    regionLabel: "International",
    stepTag: "Question 9",
    fieldBadge: "Checked",
    fieldLabel: "Tax Identification Number",
    sampleValue: "815 423 901",
    translations: {
      en: {
        question: "What is your Tax Identification Number?",
        explanation: "We check your number format immediately for typos — nothing is ever guessed for you.",
      },
      ar: {
        question: "ما هو رقم التعريف الضريبي الخاص بك؟",
        explanation: "نتحقق من صيغة الرقم فوراً لاكتشاف أي خطأ إملائي — دون أي تخمين لبياناتك.",
      },
      fr: {
        question: "Quel est votre numéro d'identification fiscale ?",
        explanation: "Nous vérifions aussitôt le format du numéro pour éviter toute faute de frappe — rien n'est jamais deviné.",
      },
      de: {
        question: "Wie lautet Ihre steuerliche Identifikationsnummer?",
        explanation: "Wir prüfen die Nummernstruktur sofort auf Tippfehler — amtliche Nummern werden niemals erraten.",
      },
      es: {
        question: "¿Cuál es su número de identificación fiscal?",
        explanation: "Comprobamos al instante el formato del número para evitar errores; nunca adivinamos sus datos.",
      },
      tr: {
        question: "Vergi kimlik numaranız nedir?",
        explanation: "Yazım hatalarına karşı numara biçimini anında kontrol ederiz; hiçbir bilgi sizin yerinize tahmin edilmez.",
      },
    },
  },
];

export default function Home() {
  const router = useRouter();
  const t = useTranslations("home");
  const tc = useTranslations("common");
  const { locale, setLocale } = useLanguage();

  const [forms, setForms] = useState<PublishedForm[]>([]);
  const [loadingForms, setLoadingForms] = useState<boolean>(true);
  const [launchingId, setLaunchingId] = useState<string | null>(null);
  const [launchError, setLaunchError] = useState<string | null>(null);

  // Showcase state
  const [selectedDocId, setSelectedDocId] = useState<string>("visa");
  const [scannerLang, setScannerLang] = useState<string>("en");
  const [catalogSearch, setCatalogSearch] = useState<string>("");
  const [catalogCategory, setCatalogCategory] = useState<string>("all");

  const activeLanguage = useMemo(() => getLanguageByCode(locale), [locale]);
  const launchLanguages = useMemo(
    () => LAUNCH_UI_CODES.map((code) => getLanguageByCode(code)),
    [],
  );

  const activeDoc = useMemo(
    () => SHOWCASE_DOCS.find((d) => d.id === selectedDocId) || SHOWCASE_DOCS[0],
    [selectedDocId],
  );

  useEffect(() => {
    let active = true;
    setLoadingForms(true);

    getPublishedForms()
      .then((items) => {
        if (!active) return;
        const getRegionPriority = (key: string) => {
          if (key.startsWith("eu-")) return 1;
          if (key.startsWith("us-")) return 2;
          if (key.startsWith("uk-")) return 3;
          if (key.startsWith("de-")) return 4;
          return 5;
        };
        const sorted = [...items].sort((a, b) => {
          const pA = getRegionPriority(a.templateKey);
          const pB = getRegionPriority(b.templateKey);
          if (pA !== pB) return pA - pB;
          return a.name.localeCompare(b.name);
        });
        setForms(sorted);
      })
      .catch(() => {
        if (active) setForms([]);
      })
      .finally(() => {
        if (active) setLoadingForms(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const handleQuickLaunch = async (form: PublishedForm) => {
    if (launchingId) return;
    setLaunchError(null);
    setLaunchingId(form.id);

    try {
      const outputLang =
        form.supportedOutputLanguages[0] || form.sourceLanguage || "de";
      const session = await createSession(form.id, locale, outputLang);
      if (session.ownershipToken) {
        setSessionToken(session.publicId, session.ownershipToken);
      }
      router.push(`/application/session/${session.publicId}`);
    } catch {
      setLaunchError(t("quickStartError"));
      setLaunchingId(null);
    }
  };

  // Filtered forms for catalog
  const filteredForms = useMemo(() => {
    return forms.filter((form) => {
      const q = catalogSearch.trim().toLowerCase();
      const matchesSearch =
        q === "" ||
        form.name.toLowerCase().includes(q) ||
        (form.description && form.description.toLowerCase().includes(q)) ||
        form.templateKey.toLowerCase().includes(q);

      if (!matchesSearch) return false;

      if (catalogCategory === "all") return true;
      if (catalogCategory === "residence") {
        return (
          form.templateKey.includes("anmeldung") ||
          form.templateKey.includes("wohnsitz") ||
          form.templateKey.includes("residence")
        );
      }
      if (catalogCategory === "family") {
        return (
          form.templateKey.includes("kindergeld") ||
          form.templateKey.includes("elterngeld") ||
          form.templateKey.includes("family")
        );
      }
      if (catalogCategory === "business") {
        return (
          form.templateKey.includes("gewerbe") ||
          form.templateKey.includes("tax") ||
          form.templateKey.includes("business")
        );
      }
      return true;
    });
  }, [forms, catalogSearch, catalogCategory]);

  return (
    <main className="relative min-h-screen bg-[#0A0E17] text-slate-100 overflow-hidden">
      {/* Background Engineering Matrix Texture */}
      <div
        className="pointer-events-none absolute inset-0 bg-lines-aikido opacity-40"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[550px] bg-[radial-gradient(ellipse_at_top,rgba(16,185,129,0.12),transparent_70%)]"
        aria-hidden="true"
      />

      <div className="relative mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-14 lg:px-8 space-y-24">
        {/* =========================================================================
            SECTION 1: Asymmetric Aikido Split Hero with Live Multilingual Scanner
            ========================================================================= */}
        <section className="grid grid-cols-1 gap-12 lg:grid-cols-12 lg:items-center pt-2">
          {/* Left Column: Main Value Proposition & Actions */}
          <div className="lg:col-span-7 space-y-6 text-start">
            {/* Simple Eyebrow Pill */}
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-semibold text-emerald-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              <span>Read in Your Language • Fill Official PDFs Accurately</span>
            </div>

            {/* Headline */}
            <h1 className="max-w-2xl text-3xl font-extrabold tracking-tight text-white sm:text-5xl sm:leading-[1.12]">
              {t("headline")}
            </h1>

            {/* Subheadline */}
            <p className="max-w-xl text-base leading-relaxed text-slate-400">
              {t("subheadline")}
            </p>

            {/* Instant 8-Language Switcher Strip */}
            <div className="space-y-2 pt-1">
              <div className="text-xs font-medium text-slate-400">
                Choose your language
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                {launchLanguages.map((lang) => {
                  const selected = locale === lang.code;
                  return (
                    <button
                      key={lang.code}
                      type="button"
                      onClick={() => setLocale(lang.code)}
                      aria-pressed={selected}
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-all ${
                        selected
                          ? "border-emerald-500 bg-emerald-500/15 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.25)] ring-1 ring-emerald-500/40"
                          : "border-white/[0.1] bg-[#0F1522] text-slate-300 hover:border-emerald-500/40 hover:bg-[#151D2E] hover:text-white"
                      }`}
                    >
                      <span>{lang.nativeName}</span>
                    </button>
                  );
                })}
                <span className="px-2 text-xs text-slate-400">
                  <bdi>+{UNIVERSAL_LANGUAGES.length - launchLanguages.length} more languages</bdi>
                </span>
              </div>
            </div>

            {/* Primary & Secondary Action Buttons */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3.5 pt-3">
              <Link
                href="/application"
                className="btn-primary px-7 py-3.5 text-sm font-bold shadow-[0_0_25px_-3px_rgba(16,185,129,0.45)]"
              >
                <UploadCloud className="h-4 w-4 shrink-0" />
                <span>{t("ctaUpload")}</span>
              </Link>

              <a
                href="#german-forms"
                className="btn-secondary px-6 py-3.5 text-sm font-semibold"
              >
                <span>{t("ctaBrowseTemplates")}</span>
              </a>
            </div>

            {/* Trust Indicators Bar */}
            <div className="pt-2 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs font-medium text-slate-400 border-t border-white/[0.08]">
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span>Your Exact Answers Only</span>
              </span>
              <span className="inline-flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span>Delete Data Anytime</span>
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5 text-emerald-400" />
                <span>Private &amp; Encrypted</span>
              </span>
            </div>
          </div>

          {/* Right Column: Interactive Form Preview Card */}
          <div className="lg:col-span-5">
            <div className="relative rounded-2xl border border-white/[0.12] bg-[#0F1522] p-5 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.85)] space-y-4 backdrop-blur-xl">
              {/* Preview Header */}
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-rose-500/80" />
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
                  <span className="ms-2 text-xs font-semibold text-slate-300">
                    Interactive Example
                  </span>
                </div>
                <div className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Live Preview</span>
                </div>
              </div>

              {/* Document Selection Tabs */}
              <div className="flex items-center gap-1 border-b border-white/[0.06] pb-2 overflow-x-auto no-scrollbar">
                {SHOWCASE_DOCS.map((doc) => (
                  <button
                    key={doc.id}
                    type="button"
                    onClick={() => setSelectedDocId(doc.id)}
                    className={`shrink-0 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
                      selectedDocId === doc.id
                        ? "bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 font-bold"
                        : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
                    }`}
                  >
                    {doc.tabLabel}
                  </button>
                ))}
              </div>

              {/* Simulated Official PDF Viewport with Animated Scan Line */}
              <div className="relative rounded-xl border border-white/[0.08] bg-[#0A0E17] p-4 text-xs overflow-hidden select-none space-y-3">
                {/* Animated Glowing Scan Beam */}
                <div
                  className="pointer-events-none absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-emerald-400 to-transparent shadow-[0_0_15px_4px_rgba(16,185,129,0.7)] animate-laser-scan z-10"
                  aria-hidden="true"
                />

                {/* Form Meta Header */}
                <div className="flex items-center justify-between text-[11px] text-slate-400 border-b border-white/[0.06] pb-2">
                  <span className="text-slate-200 font-bold">{activeDoc.title}</span>
                  <span className="rounded bg-[#151D2E] px-2 py-0.5 text-emerald-400 border border-white/[0.06]">
                    {activeDoc.regionLabel}
                  </span>
                </div>

                {/* Detected Field 1 */}
                <div className="relative rounded-lg border border-emerald-500/60 bg-emerald-500/5 p-2.5 space-y-1 shadow-[0_0_12px_rgba(16,185,129,0.1)]">
                  <div className="flex items-center justify-between text-[10px] text-emerald-400">
                    <span className="font-bold">{activeDoc.stepTag}</span>
                    <span className="bg-emerald-500/20 px-1.5 py-0.5 rounded text-[10px] font-semibold">
                      {activeDoc.fieldBadge}
                    </span>
                  </div>
                  <div className="text-xs text-slate-200 font-medium">
                    {activeDoc.fieldLabel}
                  </div>
                  <div className="text-xs text-emerald-300 bg-[#0A0E17]/80 rounded px-2.5 py-1 border border-white/[0.06] font-medium">
                    {activeDoc.sampleValue}
                  </div>
                </div>

                {/* Detected Field 2 (Signature Preview) */}
                <div className="rounded-lg border border-white/[0.08] bg-[#0F1522]/60 p-2.5 space-y-1 opacity-75">
                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span>Final Step</span>
                    <span className="text-emerald-400 font-medium">Ready to Sign</span>
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Signature &amp; Date Placement on Official Form
                  </div>
                </div>
              </div>

              {/* Bottom Real-Time Guided Translation Output */}
              <div className="rounded-xl border border-white/[0.08] bg-[#151D2E] p-3.5 space-y-2.5 text-start">
                <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                  <span className="text-xs font-semibold text-slate-300">
                    Question in Your Language
                  </span>
                  {/* Language switch tabs for live showcase */}
                  <div className="flex items-center gap-1">
                    {(["en", "ar", "fr", "de", "es", "tr"] as const).map((lang) => (
                      <button
                        key={lang}
                        type="button"
                        onClick={() => setScannerLang(lang)}
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase transition-colors ${
                          scannerLang === lang
                            ? "bg-emerald-500 text-slate-950 font-bold"
                            : "bg-[#0A0E17] text-slate-400 hover:text-white"
                        }`}
                      >
                        {lang}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Localized Question Display */}
                <div
                  dir={scannerLang === "ar" ? "rtl" : "ltr"}
                  className="space-y-1"
                >
                  <p className="text-xs font-bold text-white leading-snug">
                    <bdi>{activeDoc.translations[scannerLang]?.question}</bdi>
                  </p>
                  <p className="text-[11px] leading-relaxed text-slate-400">
                    <bdi>{activeDoc.translations[scannerLang]?.explanation}</bdi>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* =========================================================================
            SECTION 2: How It Helps You (Plain-Language Feature Cards)
            ========================================================================= */}
        <section className="space-y-6">
          <div className="max-w-2xl space-y-2 text-start">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.1] bg-[#0F1522] px-3 py-1 text-xs font-medium text-slate-300">
              <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
              <span>How It Helps You</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              Understand Every Question. Fill Every Page Accurately.
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              No confusing legal wording or manual copying. FormFlow guides you question by question in plain language and fills your exact answers onto the official form.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Tile 1 (Large - Col Span 2): Clear 3-Step Language Flow */}
            <div className="md:col-span-2 rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 sm:p-8 space-y-6 flex flex-col justify-between hover:border-emerald-500/30 transition-all duration-200">
              <div className="space-y-3 text-start">
                <div className="flex items-center justify-between">
                  <div className="inline-flex items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-300">
                    <Languages className="h-3.5 w-3.5 text-emerald-400" />
                    <span>3 Clear Steps</span>
                  </div>
                  <span className="text-xs font-medium text-slate-400">8+ Languages</span>
                </div>
                <h3 className="text-xl font-bold text-white">
                  Read in Your Language. Export in the Office&apos;s Language.
                </h3>
                <p className="text-xs sm:text-sm leading-relaxed text-slate-400 max-w-xl">
                  Even if an application is only in German, French, or English, you see every question and helpful explanation in the language you know best — while your final PDF matches what the office expects.
                </p>
              </div>

              {/* Visual 3-Step Diagram */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-start text-xs">
                <div className="rounded-xl border border-white/[0.08] bg-[#0A0E17] p-3.5 space-y-1">
                  <span className="text-[11px] text-slate-400 font-semibold block">Step 1</span>
                  <div className="font-bold text-slate-200">Original Form</div>
                  <p className="text-[11px] text-slate-400">
                    Upload your PDF or photo, or pick a ready-made official form.
                  </p>
                </div>
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 space-y-1">
                  <span className="text-[11px] text-emerald-400 font-semibold block">Step 2</span>
                  <div className="font-bold text-emerald-300">Your Language</div>
                  <p className="text-[11px] text-slate-300">
                    Answer clear, everyday questions one at a time in your own language.
                  </p>
                </div>
                <div className="rounded-xl border border-white/[0.08] bg-[#0A0E17] p-3.5 space-y-1">
                  <span className="text-[11px] text-slate-400 font-semibold block">Step 3</span>
                  <div className="font-bold text-slate-200">Ready-to-Sign PDF</div>
                  <p className="text-[11px] text-slate-400">
                    Download a neat, checked PDF ready to sign and submit.
                  </p>
                </div>
              </div>
            </div>

            {/* Tile 2: Automatic Mistake Checks */}
            <div className="rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 space-y-5 flex flex-col justify-between hover:border-emerald-500/30 transition-all duration-200">
              <div className="space-y-3 text-start">
                <div className="inline-flex items-center gap-2 rounded-md border border-white/[0.08] bg-[#151D2E] px-2.5 py-1 text-xs font-semibold text-slate-300">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Built-In Checks</span>
                </div>
                <h3 className="text-lg font-bold text-white">
                  Automatic Format Checks
                </h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  Dates, bank IBAN numbers, email addresses, and postal codes are checked automatically for typos before you download.
                </p>
              </div>

              {/* Clean Visual Checklist Tile (No Python Code) */}
              <div className="rounded-xl border border-white/[0.08] bg-[#0A0E17] p-3.5 text-xs text-slate-300 space-y-2 select-none">
                <div className="flex items-center gap-2 text-emerald-400 font-medium">
                  <Check className="h-3.5 w-3.5 shrink-0" />
                  <span>Date format checked</span>
                </div>
                <div className="flex items-center gap-2 text-emerald-400 font-medium">
                  <Check className="h-3.5 w-3.5 shrink-0" />
                  <span>Bank IBAN number verified</span>
                </div>
                <div className="flex items-center gap-2 text-emerald-400 font-medium">
                  <Check className="h-3.5 w-3.5 shrink-0" />
                  <span>Required boxes completed</span>
                </div>
              </div>
            </div>

            {/* Tile 3: Saved Details & Privacy */}
            <div className="rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 space-y-5 flex flex-col justify-between hover:border-emerald-500/30 transition-all duration-200">
              <div className="space-y-3 text-start">
                <div className="inline-flex items-center gap-2 rounded-md border border-white/[0.08] bg-[#151D2E] px-2.5 py-1 text-xs font-semibold text-slate-300">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Private &amp; Under Your Control</span>
                </div>
                <h3 className="text-lg font-bold text-white">
                  Save Details for Next Time — Delete Anytime
                </h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  Guest sessions remove themselves automatically after 24 hours. Registered users can reuse saved contact details safely and erase everything in one click.
                </p>
              </div>

              <div className="rounded-xl border border-white/[0.08] bg-[#0A0E17] p-3 text-xs flex items-center justify-between text-slate-300 font-medium">
                <span className="text-emerald-400 font-semibold">Encrypted Storage</span>
                <span>1-Click Delete</span>
              </div>
            </div>

            {/* Tile 4 (Col Span 2): Clean Multi-Page PDF Download */}
            <div className="md:col-span-2 rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 sm:p-8 space-y-5 flex flex-col justify-between hover:border-emerald-500/30 transition-all duration-200">
              <div className="space-y-3 text-start">
                <div className="inline-flex items-center gap-2 rounded-md border border-white/[0.08] bg-[#151D2E] px-2.5 py-1 text-xs font-semibold text-slate-300">
                  <FileText className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Ready-to-Print Official PDFs</span>
                </div>
                <h3 className="text-xl font-bold text-white">
                  Multi-Page Forms &amp; Hand-Drawn Signatures
                </h3>
                <p className="text-xs sm:text-sm leading-relaxed text-slate-400 max-w-xl">
                  Every answer, checkbox, and signature goes neatly into the right spot on every page — supporting international letters, accents, and Arabic scripts cleanly.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3 pt-2 text-xs font-medium text-slate-300">
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-[#0A0E17] px-3 py-1.5">
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Every PDF Page Filled</span>
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-[#0A0E17] px-3 py-1.5">
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  <span>International &amp; Arabic Text</span>
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-[#0A0E17] px-3 py-1.5">
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Side-by-Side Answer Review</span>
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* =========================================================================
            SECTION 3: Popular Ready-to-Use Official Forms
            ========================================================================= */}
        <section
          id="german-forms"
          className="rounded-2xl border border-white/[0.1] bg-[#0F1522] overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.7)]"
        >
          {/* Header & Filter Controls */}
          <div className="border-b border-white/[0.08] bg-[#151D2E]/80 p-6 sm:p-8 space-y-5">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="space-y-1 text-start">
                <div className="inline-flex items-center gap-2 text-xs text-emerald-400 font-bold">
                  <FileText className="h-3.5 w-3.5" />
                  <span>Ready-to-Use Forms</span>
                </div>
                <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                  {t("quickStartTitle")}
                </h2>
                <p className="text-xs sm:text-sm text-slate-400">
                  {t("quickStartSubtitle", { language: activeLanguage.nativeName })}
                </p>
              </div>

              {/* Search Bar */}
              <div className="relative w-full md:w-72">
                <Search className="pointer-events-none absolute start-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  value={catalogSearch}
                  onChange={(e) => setCatalogSearch(e.target.value)}
                  placeholder="Search forms by topic or country..."
                  className="w-full rounded-xl border border-white/[0.1] bg-[#0A0E17] py-2 ps-9 pe-3 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/30"
                />
              </div>
            </div>

            {/* Category Filter Pills */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              {[
                { key: "all", label: "All Forms" },
                { key: "residence", label: "Home & Residence" },
                { key: "family", label: "Family & Benefits" },
                { key: "business", label: "Work & Taxes" },
              ].map((cat) => (
                <button
                  key={cat.key}
                  type="button"
                  onClick={() => setCatalogCategory(cat.key)}
                  className={`rounded-lg px-3 py-1 text-xs font-semibold transition-colors ${
                    catalogCategory === cat.key
                      ? "bg-emerald-500 text-slate-950 font-bold"
                      : "bg-[#0A0E17] text-slate-400 hover:text-white border border-white/[0.06]"
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>

            {launchError && (
              <div
                role="alert"
                className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-xs font-medium text-rose-300"
              >
                {launchError}
              </div>
            )}
          </div>

          {/* Form Grid List */}
          {loadingForms ? (
            <div className="px-6 py-12 text-center text-sm text-slate-500">
              {tc("loading")}
            </div>
          ) : filteredForms.length === 0 ? (
            <div className="px-6 py-10 sm:px-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <p className="text-sm text-slate-400">{t("step1Body")}</p>
              <Link
                href="/application"
                className="btn-primary shrink-0 px-5 py-2.5 text-xs font-bold"
              >
                {t("ctaUpload")}
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 divide-y divide-white/[0.08] md:grid-cols-2 md:divide-y-0">
              {filteredForms.slice(0, 16).map((form, index) => {
                const isLaunching = launchingId === form.id;
                const rowBorder = index >= 2 ? "md:border-t md:border-white/[0.08]" : "";
                const colBorder = index % 2 === 1 ? "md:border-s md:border-white/[0.08]" : "";

                const getJurisdictionBadge = (key: string) => {
                  if (key.startsWith("eu-")) return "European Union";
                  if (key.startsWith("us-")) return "United States";
                  if (key.startsWith("uk-")) return "United Kingdom";
                  if (key.startsWith("ca-")) return "Canada";
                  if (key.startsWith("de-")) return "Germany";
                  return "International";
                };
                const regionName = getJurisdictionBadge(form.templateKey);
                const formLangName = getLanguageByCode(form.sourceLanguage).nativeName;

                return (
                  <div
                    key={form.id}
                    className={`flex flex-col justify-between gap-4 p-5 sm:px-7 sm:py-6 transition-all duration-200 hover:bg-[#151D2E]/80 ${rowBorder} ${colBorder}`}
                  >
                    <div className="space-y-2 text-start">
                      <div className="flex items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-1.5 rounded border border-white/[0.1] bg-[#0A0E17] px-2.5 py-0.5 text-[11px] font-semibold text-emerald-400">
                          {regionName}
                        </span>
                        <span className="rounded border border-white/[0.08] bg-[#0A0E17] px-2.5 py-0.5 text-[11px] font-medium text-slate-400">
                          Form in {formLangName}
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-white">
                        <bdi>{form.name}</bdi>
                      </h3>
                      {form.description && (
                        <p className="text-xs leading-relaxed text-slate-400 line-clamp-2">
                          <bdi>{form.description}</bdi>
                        </p>
                      )}
                    </div>

                    <div className="flex items-center justify-end pt-2">
                      <button
                        type="button"
                        data-testid={`quick-launch-${form.templateKey}`}
                        disabled={Boolean(launchingId)}
                        onClick={() => handleQuickLaunch(form)}
                        className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-xs font-bold text-emerald-300 transition-all hover:bg-emerald-500/20 hover:border-emerald-500/50 disabled:opacity-50"
                      >
                        <span>
                          {isLaunching
                            ? t("quickStartLaunching")
                            : t("quickStartAction", {
                                language: activeLanguage.nativeName,
                              })}
                        </span>
                        <ArrowRight className="h-3.5 w-3.5 text-emerald-400" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* =========================================================================
            SECTION 4: Three Simple Promises (Privacy, Accuracy, Clarity)
            ========================================================================= */}
        <section className="grid grid-cols-1 gap-6 md:grid-cols-3 border-y border-white/[0.08] py-12">
          <div className="space-y-2 text-start">
            <div className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-bold">
              <ShieldCheck className="h-4 w-4" />
              <span>Your Privacy First</span>
            </div>
            <h2 className="text-sm font-bold text-white">
              {t("trustEuTitle")}
            </h2>
            <p className="text-xs leading-relaxed text-slate-400">
              {t("trustEuBody")}
            </p>
          </div>
          <div className="space-y-2 text-start">
            <div className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-bold">
              <CheckCircle2 className="h-4 w-4" />
              <span>Built-In Checks</span>
            </div>
            <h2 className="text-sm font-bold text-white">
              {t("trustAccuracyTitle")}
            </h2>
            <p className="text-xs leading-relaxed text-slate-400">
              {t("trustAccuracyBody")}
            </p>
          </div>
          <div className="space-y-2 text-start">
            <div className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-bold">
              <Lock className="h-4 w-4" />
              <span>Honest Guidance</span>
            </div>
            <h2 className="text-sm font-bold text-white">
              {t("trustRdgTitle")}
            </h2>
            <p className="text-xs leading-relaxed text-slate-400">
              {t("trustRdgBody")}
            </p>
          </div>
        </section>

        {/* =========================================================================
            SECTION 5: Simple Pricing Preview
            ========================================================================= */}
        <section className="space-y-8 pb-8">
          <div className="max-w-2xl space-y-2 text-start">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.1] bg-[#0F1522] px-3 py-1 text-xs font-medium text-slate-300">
              <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
              <span>Simple, Clear Pricing</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              {t("pricingTitle")}
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              {t("pricingSubtitle")}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {/* Free Starter */}
            <div className="rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 sm:p-7 flex flex-col justify-between gap-6 hover:border-white/[0.2] transition-colors">
              <div className="space-y-3.5 text-start">
                <span className="text-xs text-slate-400 font-semibold block">Free Starter</span>
                <h3 className="text-lg font-bold text-white">
                  {t("planFreeName")}
                </h3>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-white tabular-nums">
                    <bdi>{t("planFreePrice")}</bdi>
                  </span>
                  <span className="text-xs text-slate-400">
                    {t("planFreeUnit")}
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-slate-400">
                  {t("planFreeDesc")}
                </p>
              </div>
              <Link
                href="/application"
                className="btn-secondary w-full py-2.5 text-xs font-bold"
              >
                {t("ctaUpload")}
              </Link>
            </div>

            {/* Agency Pro */}
            <div className="rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 sm:p-7 flex flex-col justify-between gap-6 hover:border-white/[0.2] transition-colors">
              <div className="space-y-3.5 text-start">
                <span className="text-xs text-emerald-400 font-semibold block">For Agencies &amp; Teams</span>
                <h3 className="text-lg font-bold text-white">
                  {t("planSingleName")}
                </h3>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-white tabular-nums">
                    <bdi>{t("planSinglePrice")}</bdi>
                  </span>
                  <span className="text-xs text-slate-400">
                    {t("planSingleUnit")}
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-slate-400">
                  {t("planSingleDesc")}
                </p>
              </div>
              <Link
                href="/application"
                className="btn-secondary w-full py-2.5 text-xs font-bold"
              >
                {t("ctaUpload")}
              </Link>
            </div>

            {/* Teams & Offices (Highlighted) */}
            <div className="relative rounded-2xl border-2 border-emerald-500 bg-[#0F1522] p-6 sm:p-7 flex flex-col justify-between gap-6 shadow-[0_0_30px_-5px_rgba(16,185,129,0.3)]">
              <div className="space-y-3.5 text-start">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-emerald-400 font-semibold block">For Larger Offices</span>
                  <span className="rounded-full bg-emerald-500/20 border border-emerald-500/50 px-2.5 py-0.5 text-[11px] font-bold text-emerald-300">
                    {t("planPackBadge")}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white">
                  {t("planPackName")}
                </h3>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-white tabular-nums">
                    <bdi>{t("planPackPrice")}</bdi>
                  </span>
                  <span className="text-xs text-slate-400">
                    {t("planPackUnit")}
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-slate-300">
                  {t("planPackDesc")}
                </p>
              </div>
              <Link
                href="/application"
                className="btn-primary w-full py-2.5 text-xs font-bold shadow-[0_0_20px_rgba(16,185,129,0.4)]"
              >
                {t("ctaUpload")}
              </Link>
            </div>
          </div>

          <p className="text-xs text-slate-400 text-start">
            {t("planAgencyNote")}
          </p>
        </section>
      </div>
    </main>
  );
}
