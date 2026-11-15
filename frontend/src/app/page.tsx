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
  Database,
  Code2,
  Cpu,
  Layers,
  Sparkles,
  Check,
  Terminal,
} from "lucide-react";

const LAUNCH_UI_CODES = ["en", "de", "fr", "ar", "tr", "uk", "es", "ru"] as const;

interface ShowcaseDoc {
  id: string;
  title: string;
  ref: string;
  jurisdiction: string;
  fieldId: string;
  fieldType: string;
  fieldLabel: string;
  sampleValue: string;
  translations: Record<string, { question: string; explanation: string }>;
}

const SHOWCASE_DOCS: ShowcaseDoc[] = [
  {
    id: "visa",
    title: "International Visa & Work Permit Intake",
    ref: "REF: VISA-INT-2026",
    jurisdiction: "GLOBAL",
    fieldId: "01_FULL_LEGAL_NAME",
    fieldType: "TEXT_CANONICAL",
    fieldLabel: "Applicant Full Legal Name (Passport Standard)",
    sampleValue: "Dr. Elena Rostova",
    translations: {
      en: {
        question: "What is your full legal name as shown on your passport?",
        explanation: "Enter your first name, middle names (if any), and family name in Roman script exactly as they appear in your official travel document.",
      },
      ar: {
        question: "ما هو اسمك القانوني الكامل كما هو موضح في جواز السفر؟",
        explanation: "أدخل اسمك الأول والاسم الأوسط واسم العائلة بالأحرف اللاتينية تماماً كما تظهر في وثيقة السفر الرسمية الخاصة بك.",
      },
      fr: {
        question: "Quel est votre nom légal complet tel qu'il figure sur votre passeport ?",
        explanation: "Indiquez votre prénom, vos éventuels autres prénoms et votre nom de famille en caractères latins, exactement tels qu'ils figurent sur votre document officiel.",
      },
      de: {
        question: "Wie lautet Ihr vollständiger amtlicher Name laut Reisepass?",
        explanation: "Geben Sie Vornamen und Nachnamen exakt so ein, wie sie in Ihrem amtlichen Reisedokument aufgeführt sind.",
      },
      es: {
        question: "¿Cuál es su nombre legal completo según figura en su pasaporte?",
        explanation: "Escriba su nombre, segundos nombres y apellidos en alfabeto latino exactamente como aparecen en su documento de viaje oficial.",
      },
      tr: {
        question: "Pasaportunuzda görünen tam yasal adınız nedir?",
        explanation: "Adınızı ve soyadınızı resmi seyahat belgenizde yer aldığı şekilde Latin harfleriyle tam olarak girin.",
      },
    },
  },
  {
    id: "residence",
    title: "Official Address Registration Certificate",
    ref: "REF: CIV-REG-840",
    jurisdiction: "EU",
    fieldId: "04_DATE_OF_MOVE_IN",
    fieldType: "DATE_ISO8601",
    fieldLabel: "Official Date of Occupancy / Move-In",
    sampleValue: "2026-03-01",
    translations: {
      en: {
        question: "On what date did you officially move into this residence?",
        explanation: "Provide the tenancy start date in ISO format. Deterministic rules verify this matches your landlord confirmation.",
      },
      ar: {
        question: "في أي تاريخ انتقلت رسمياً إلى هذا السكن؟",
        explanation: "حدد تاريخ بدء الإقامة بتنسيق تاريخ قياسي. تؤكد القواعد الحسابية تطابق التاريخ مع إفادة المالك.",
      },
      fr: {
        question: "À quelle date avez-vous emménagé dans ce logement ?",
        explanation: "Indiquez la date d'emménagement officielle. Nos règles déterministes vérifient la concordance avec l'attestation de bail.",
      },
      de: {
        question: "An welchem Tag sind Sie offiziell in die Wohnung eingezogen?",
        explanation: "Geben Sie das Einzugsdatum an. Die Angabe wird deterministisch auf Übereinstimmung mit der Wohnungsgeberbestätigung geprüft.",
      },
      es: {
        question: "¿En qué fecha se mudó oficialmente a esta residencia?",
        explanation: "Indique la fecha de inicio del alquiler. Las reglas deterministas verifican que coincida con la confirmación del propietario.",
      },
      tr: {
        question: "Bu konuta resmi olarak hangi tarihte taşındınız?",
        explanation: "Kira başlangıç tarihini belirtin. Deterministik kurallar bu tarihin ev sahibi onayıyla eşleştiğini doğrular.",
      },
    },
  },
  {
    id: "tax",
    title: "Tax Registration & Compliance Declaration",
    ref: "REF: TAX-DEC-991",
    jurisdiction: "OECD",
    fieldId: "09_TAX_IDENTIFIER",
    fieldType: "CHECKSUM_VALIDATED",
    fieldLabel: "Tax Identification Number / TIN",
    sampleValue: "TIN 815 423 901",
    translations: {
      en: {
        question: "What is your primary Tax Identification Number (TIN)?",
        explanation: "Our deterministic engine verifies MOD-97 checksums immediately. Zero AI guessing is applied to statutory numbers.",
      },
      ar: {
        question: "ما هو رقم التعريف الضريبي الأساسي الخاص بك؟",
        explanation: "يتحقق محركنا الرياضي من صحة أرقام التحقق فوراً دون أي تخمين من الذكاء الاصطناعي.",
      },
      fr: {
        question: "Quel est votre numéro d'identification fiscale (NIF) ?",
        explanation: "Notre moteur mathématique vérifie instantanément les clés de contrôle sans aucune approximation d'intelligence artificielle.",
      },
      de: {
        question: "Wie lautet Ihre steuerliche Identifikationsnummer (IdNr)?",
        explanation: "Unsere Prüfengine validiert die Prüfziffer deterministisch ohne spekulative KI-Eingriffe.",
      },
      es: {
        question: "¿Cuál es su número de identificación fiscal (NIF/TIN)?",
        explanation: "Nuestro motor algorítmico verifica los dígitos de control de inmediato sin conjeturas de IA.",
      },
      tr: {
        question: "Vergi Kimlik Numaranız (VKN) nedir?",
        explanation: "Algoritmik motorumuz kontrol basamaklarını anında doğrular; resmi rakamlar asla yapay zeka ile tahmin edilmez.",
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
          {/* Left Column: High-Contrast Technical Command Content */}
          <div className="lg:col-span-7 space-y-6 text-start">
            {/* Technical Signal Eyebrow */}
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-mono font-medium text-emerald-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>UNIVERSAL ADMINISTRATIVE FORM INTELLIGENCE • 100% DETERMINISTIC</span>
            </div>

            {/* High-Contrast Geometric Sans Headline */}
            <h1 className="max-w-2xl text-3xl font-extrabold tracking-tight text-white sm:text-5xl sm:leading-[1.12]">
              {t("headline")}
            </h1>

            {/* Anti-Slop Architectural Subheadline */}
            <p className="max-w-xl text-base leading-relaxed text-slate-400">
              {t("subheadline")}
            </p>

            {/* Instant 8-Language Switcher Strip (Flag-Free & Clean) */}
            <div className="space-y-2 pt-1">
              <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
                Active Interface Language
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
                      <span className="font-mono text-[10px] uppercase font-bold text-emerald-400">
                        {lang.code}
                      </span>
                      <span>{lang.nativeName}</span>
                    </button>
                  );
                })}
                <span className="px-2 text-xs font-mono text-slate-500">
                  <bdi>+{UNIVERSAL_LANGUAGES.length - launchLanguages.length} MORE</bdi>
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
            <div className="pt-2 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs font-mono text-slate-400 border-t border-white/[0.08]">
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span>0% AI HALLUCINATION</span>
              </span>
              <span className="inline-flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span>GDPR ART. 17/20</span>
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5 text-emerald-400" />
                <span>AES-256 FERNET</span>
              </span>
            </div>
          </div>

          {/* Right Column: Live Animated Multilingual Form Scanner & Pipeline Card */}
          <div className="lg:col-span-5">
            <div className="relative rounded-2xl border border-white/[0.12] bg-[#0F1522] p-5 shadow-[0_20px_60px_-15px_rgba(0,0,0,0.85)] space-y-4 backdrop-blur-xl">
              {/* Terminal Command Header */}
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-rose-500/80" />
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-500/80" />
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80" />
                  <span className="ms-2 font-mono text-[11px] font-semibold text-slate-300">
                    REAL-TIME FORM SCANNER
                  </span>
                </div>
                <div className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>BEAM: ACTIVE</span>
                </div>
              </div>

              {/* Document Selection Tabs */}
              <div className="flex items-center gap-1 border-b border-white/[0.06] pb-2 overflow-x-auto no-scrollbar">
                {SHOWCASE_DOCS.map((doc) => (
                  <button
                    key={doc.id}
                    type="button"
                    onClick={() => setSelectedDocId(doc.id)}
                    className={`shrink-0 rounded-lg px-2.5 py-1 text-[11px] font-mono transition-colors ${
                      selectedDocId === doc.id
                        ? "bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 font-bold"
                        : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
                    }`}
                  >
                    {doc.id.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* Simulated Official PDF Viewport with Animated Laser Beam */}
              <div className="relative rounded-xl border border-white/[0.08] bg-[#0A0E17] p-4 font-mono text-xs overflow-hidden select-none space-y-3">
                {/* Animated Glowing Laser Scanning Beam */}
                <div
                  className="pointer-events-none absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-emerald-400 to-transparent shadow-[0_0_15px_4px_rgba(16,185,129,0.7)] animate-laser-scan z-10"
                  aria-hidden="true"
                />

                {/* Form Meta Header */}
                <div className="flex items-center justify-between text-[10px] text-slate-500 border-b border-white/[0.06] pb-2">
                  <span className="text-slate-300 font-bold">{activeDoc.title}</span>
                  <span className="rounded bg-[#151D2E] px-1.5 py-0.5 text-emerald-400 border border-white/[0.06]">
                    {activeDoc.jurisdiction}
                  </span>
                </div>

                {/* Detected Bounding Box Field 1 (Scanned) */}
                <div className="relative rounded-lg border border-emerald-500/60 bg-emerald-500/5 p-2.5 space-y-1 shadow-[0_0_12px_rgba(16,185,129,0.1)]">
                  <div className="flex items-center justify-between text-[9px] text-emerald-400">
                    <span className="font-bold">[{activeDoc.fieldId}]</span>
                    <span className="bg-emerald-500/20 px-1 py-0.2 rounded text-[8px] font-bold">
                      {activeDoc.fieldType}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-300 font-sans font-medium">
                    {activeDoc.fieldLabel}
                  </div>
                  <div className="text-[10px] text-emerald-300 font-mono bg-[#0A0E17]/80 rounded px-2 py-0.5 border border-white/[0.06]">
                    {activeDoc.sampleValue}
                  </div>
                </div>

                {/* Detected Bounding Box Field 2 (Passive context) */}
                <div className="rounded-lg border border-white/[0.08] bg-[#0F1522]/60 p-2 space-y-1 opacity-60">
                  <div className="flex items-center justify-between text-[9px] text-slate-500">
                    <span>[FIELD: 08_VERIFICATION_STATUS]</span>
                    <span>DETERMINISTIC_PASS</span>
                  </div>
                  <div className="text-[10px] text-slate-400 font-sans">
                    Authority Signature & Official Seal Placeholder
                  </div>
                </div>
              </div>

              {/* Bottom Real-Time Guided Translation Output */}
              <div className="rounded-xl border border-white/[0.08] bg-[#151D2E] p-3.5 space-y-2.5 text-start">
                <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
                    Live Multilingual Guided Question
                  </span>
                  {/* Language switch tabs for live showcase */}
                  <div className="flex items-center gap-1">
                    {(["en", "ar", "fr", "de", "es", "tr"] as const).map((lang) => (
                      <button
                        key={lang}
                        type="button"
                        onClick={() => setScannerLang(lang)}
                        className={`px-1.5 py-0.5 rounded font-mono text-[9px] font-bold uppercase transition-colors ${
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
            SECTION 2: Aikido Asymmetric Modular Bento Grid Architecture
            ========================================================================= */}
        <section className="space-y-6">
          <div className="max-w-2xl space-y-2 text-start">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.1] bg-[#0F1522] px-3 py-1 font-mono text-xs text-slate-300">
              <Cpu className="h-3.5 w-3.5 text-emerald-400" />
              <span>CORE ARCHITECTURAL INVARIANTS</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              Zero AI Hallucinations. Sovereign Compliance.
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              Standard LLM wrappers fail on official civic documents because they guess missing numbers and mutate legal records. FormFlow enforces mathematical determinism.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Tile 1 (Large - Col Span 2): 3-Language Isolated Engine */}
            <div className="md:col-span-2 rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 sm:p-8 space-y-6 flex flex-col justify-between hover:border-emerald-500/30 transition-all duration-200">
              <div className="space-y-3 text-start">
                <div className="flex items-center justify-between">
                  <div className="inline-flex items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-xs font-mono font-semibold text-emerald-300">
                    <Layers className="h-3.5 w-3.5 text-emerald-400" />
                    <span>3-LANGUAGE ISOLATED ENGINE</span>
                  </div>
                  <span className="font-mono text-xs text-slate-500">ISO 639-1 BOUND</span>
                </div>
                <h3 className="text-xl font-bold text-white">
                  Strict 3-Language Layer Separation
                </h3>
                <p className="text-xs sm:text-sm leading-relaxed text-slate-400 max-w-xl">
                  Unlike naive translation tools that collapse state into one string, FormFlow tracks three immutable language dimensions across every workflow: the source document language, the applicant&apos;s native guidance language, and the target official PDF output.
                </p>
              </div>

              {/* Visual Pipeline Diagram */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-start font-mono text-xs">
                <div className="rounded-xl border border-white/[0.08] bg-[#0A0E17] p-3.5 space-y-1">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block">01 / Ingestion</span>
                  <div className="font-bold text-slate-200">sourceLanguage</div>
                  <p className="text-[11px] text-slate-400 font-sans">
                    Original untrusted PDF (German, French, Spanish, etc.)
                  </p>
                </div>
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 space-y-1">
                  <span className="text-[10px] text-emerald-400 uppercase font-bold block">02 / Citizen UI</span>
                  <div className="font-bold text-emerald-300">userLanguage</div>
                  <p className="text-[11px] text-slate-300 font-sans">
                    Plain-language questions & RTL support in applicant&apos;s tongue
                  </p>
                </div>
                <div className="rounded-xl border border-white/[0.08] bg-[#0A0E17] p-3.5 space-y-1">
                  <span className="text-[10px] text-slate-500 uppercase font-bold block">03 / PDF Output</span>
                  <div className="font-bold text-slate-200">outputLanguage</div>
                  <p className="text-[11px] text-slate-400 font-sans">
                    100% compliant AcroForm compilation ready for authority signature
                  </p>
                </div>
              </div>
            </div>

            {/* Tile 2: Deterministic Python Validator */}
            <div className="rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 space-y-5 flex flex-col justify-between hover:border-emerald-500/30 transition-all duration-200">
              <div className="space-y-3 text-start">
                <div className="inline-flex items-center gap-2 rounded-md border border-white/[0.08] bg-[#151D2E] px-2.5 py-1 text-xs font-mono font-semibold text-slate-300">
                  <Code2 className="h-3.5 w-3.5 text-emerald-400" />
                  <span>DETERMINISTIC VALIDATION</span>
                </div>
                <h3 className="text-lg font-bold text-white">
                  Zero AI Guesswork
                </h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  IBANs, dates, tax numbers, and postal codes are strictly verified by deterministic code algorithms — never guessed by generative models.
                </p>
              </div>

              {/* Code Snippet Tile */}
              <div className="rounded-xl border border-white/[0.08] bg-[#0A0E17] p-3 font-mono text-[10px] text-slate-300 space-y-1 select-none">
                <div className="text-slate-500"># Verification Gate</div>
                <div><span className="text-emerald-400">assert</span> iban_checksum(val)</div>
                <div><span className="text-emerald-400">assert</span> date_iso8601(val)</div>
                <div className="text-emerald-300 pt-1">STATUS: 100% DETERMINISTIC</div>
              </div>
            </div>

            {/* Tile 3: Fernet Profile Vault & Art. 17 Shredder */}
            <div className="rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 space-y-5 flex flex-col justify-between hover:border-emerald-500/30 transition-all duration-200">
              <div className="space-y-3 text-start">
                <div className="inline-flex items-center gap-2 rounded-md border border-white/[0.08] bg-[#151D2E] px-2.5 py-1 text-xs font-mono font-semibold text-slate-300">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  <span>FERNET PROFILE VAULT</span>
                </div>
                <h3 className="text-lg font-bold text-white">
                  GDPR Art. 17 Data Shredder
                </h3>
                <p className="text-xs leading-relaxed text-slate-400">
                  Client-side Fernet encryption guarantees zero plaintext exposure. 1-click permanent data destruction erases all answers, documents, and tokens instantly.
                </p>
              </div>

              <div className="rounded-xl border border-white/[0.08] bg-[#0A0E17] p-3 text-xs font-mono flex items-center justify-between text-slate-400">
                <span className="text-emerald-400 font-bold">AES-256-CBC</span>
                <span>0-PII RETENTION</span>
              </div>
            </div>

            {/* Tile 4 (Col Span 2): Pixel-Perfect AcroForm Unicode Export */}
            <div className="md:col-span-2 rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 sm:p-8 space-y-5 flex flex-col justify-between hover:border-emerald-500/30 transition-all duration-200">
              <div className="space-y-3 text-start">
                <div className="inline-flex items-center gap-2 rounded-md border border-white/[0.08] bg-[#151D2E] px-2.5 py-1 text-xs font-mono font-semibold text-slate-300">
                  <FileText className="h-3.5 w-3.5 text-emerald-400" />
                  <span>ACROFORM UNICODE COMPILATION</span>
                </div>
                <h3 className="text-xl font-bold text-white">
                  Multi-Page AcroForm & Vector Signature Export
                </h3>
                <p className="text-xs sm:text-sm leading-relaxed text-slate-400 max-w-xl">
                  FormFlow compiles official PDFs across all pages with embedded Unicode font shaping (NotoSans / NotoSansArabic), coordinate overlays, and isolated biometric signature placement.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3 pt-2 text-xs font-mono text-slate-300">
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-[#0A0E17] px-3 py-1.5">
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  <span>All-Pages AcroForm Widget Fill</span>
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-[#0A0E17] px-3 py-1.5">
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  <span>NotoSans Arabic Font Shaping</span>
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-[#0A0E17] px-3 py-1.5">
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Watermarked Review Studio</span>
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* =========================================================================
            SECTION 3: Official Forms Architectural Catalog
            ========================================================================= */}
        <section
          id="german-forms"
          className="rounded-2xl border border-white/[0.1] bg-[#0F1522] overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.7)]"
        >
          {/* Header & Filter Controls */}
          <div className="border-b border-white/[0.08] bg-[#151D2E]/80 p-6 sm:p-8 space-y-5">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="space-y-1 text-start">
                <div className="inline-flex items-center gap-2 font-mono text-xs text-emerald-400 font-bold uppercase tracking-wider">
                  <Database className="h-3.5 w-3.5" />
                  <span>VERIFIED REGISTRY</span>
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
                  placeholder="Filter forms or jurisdiction..."
                  className="w-full rounded-xl border border-white/[0.1] bg-[#0A0E17] py-2 ps-9 pe-3 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/30"
                />
              </div>
            </div>

            {/* Category Filter Pills */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              {[
                { key: "all", label: "All Templates" },
                { key: "residence", label: "Civil & Residence" },
                { key: "family", label: "Family & Social" },
                { key: "business", label: "Tax & Business" },
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
            <div className="px-6 py-12 text-center text-sm font-mono text-slate-500">
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
                  if (key.startsWith("eu-")) return { code: "EU", name: "European Union" };
                  if (key.startsWith("us-")) return { code: "US", name: "United States" };
                  if (key.startsWith("uk-")) return { code: "UK", name: "United Kingdom" };
                  if (key.startsWith("ca-")) return { code: "CA", name: "Canada" };
                  if (key.startsWith("de-")) return { code: "DE", name: "Germany" };
                  return { code: "GLOBAL", name: "Universal Form" };
                };
                const badge = getJurisdictionBadge(form.templateKey);

                return (
                  <div
                    key={form.id}
                    className={`flex flex-col justify-between gap-4 p-5 sm:px-7 sm:py-6 transition-all duration-200 hover:bg-[#151D2E]/80 ${rowBorder} ${colBorder}`}
                  >
                    <div className="space-y-2 text-start">
                      <div className="flex items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-1.5 rounded border border-white/[0.1] bg-[#0A0E17] px-2 py-0.5 text-[10px] font-mono font-semibold text-emerald-400">
                          <span className="font-bold">{badge.code}</span>
                          <span className="text-slate-400">• {badge.name}</span>
                        </span>
                        <span
                          className="rounded border border-white/[0.08] bg-[#0A0E17] px-2 py-0.5 font-mono text-[10px] font-semibold uppercase text-slate-400"
                          dir="ltr"
                        >
                          {form.sourceLanguage.toUpperCase()} • OFFICIAL PDF
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
            SECTION 4: Three Trust & Regulatory Guardrails (High-Contrast Aikido Cards)
            ========================================================================= */}
        <section className="grid grid-cols-1 gap-6 md:grid-cols-3 border-y border-white/[0.08] py-12">
          <div className="space-y-2 text-start">
            <div className="inline-flex items-center gap-1.5 font-mono text-xs text-emerald-400 font-bold">
              <ShieldCheck className="h-4 w-4" />
              <span>EU & GLOBAL PRIVACY</span>
            </div>
            <h2 className="text-sm font-bold text-white">
              {t("trustEuTitle")}
            </h2>
            <p className="text-xs leading-relaxed text-slate-400">
              {t("trustEuBody")}
            </p>
          </div>
          <div className="space-y-2 text-start">
            <div className="inline-flex items-center gap-1.5 font-mono text-xs text-emerald-400 font-bold">
              <CheckCircle2 className="h-4 w-4" />
              <span>DETERMINISTIC ACCURACY</span>
            </div>
            <h2 className="text-sm font-bold text-white">
              {t("trustAccuracyTitle")}
            </h2>
            <p className="text-xs leading-relaxed text-slate-400">
              {t("trustAccuracyBody")}
            </p>
          </div>
          <div className="space-y-2 text-start">
            <div className="inline-flex items-center gap-1.5 font-mono text-xs text-emerald-400 font-bold">
              <Lock className="h-4 w-4" />
              <span>COMPLIANCE BOUNDARY</span>
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
            SECTION 5: Transparent Pricing Architecture (High-Contrast Dark Cards)
            ========================================================================= */}
        <section className="space-y-8 pb-8">
          <div className="max-w-2xl space-y-2 text-start">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.1] bg-[#0F1522] px-3 py-1 font-mono text-xs text-slate-300">
              <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
              <span>COMMERCIAL LICENSING & PACKAGES</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              {t("pricingTitle")}
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              {t("pricingSubtitle")}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {/* Free Sandbox */}
            <div className="rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 sm:p-7 flex flex-col justify-between gap-6 hover:border-white/[0.2] transition-colors">
              <div className="space-y-3.5 text-start">
                <span className="font-mono text-xs uppercase text-slate-400 font-bold block">EVALUATION</span>
                <h3 className="text-lg font-bold text-white">
                  {t("planFreeName")}
                </h3>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-white tabular-nums">
                    <bdi>{t("planFreePrice")}</bdi>
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
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

            {/* Single Document / Agency Pro */}
            <div className="rounded-2xl border border-white/[0.1] bg-[#0F1522] p-6 sm:p-7 flex flex-col justify-between gap-6 hover:border-white/[0.2] transition-colors">
              <div className="space-y-3.5 text-start">
                <span className="font-mono text-xs uppercase text-emerald-400 font-bold block">PROFESSIONAL</span>
                <h3 className="text-lg font-bold text-white">
                  {t("planSingleName")}
                </h3>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-white tabular-nums">
                    <bdi>{t("planSinglePrice")}</bdi>
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
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

            {/* Enterprise & Public Sector (Highlighted) */}
            <div className="relative rounded-2xl border-2 border-emerald-500 bg-[#0F1522] p-6 sm:p-7 flex flex-col justify-between gap-6 shadow-[0_0_30px_-5px_rgba(16,185,129,0.3)]">
              <div className="space-y-3.5 text-start">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs uppercase text-emerald-400 font-bold block">GOVERNMENT & B2B</span>
                  <span className="rounded-full bg-emerald-500/20 border border-emerald-500/50 px-2.5 py-0.5 text-[10px] font-mono font-bold text-emerald-300">
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
                  <span className="text-xs text-slate-400 font-mono">
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

          <p className="text-xs font-mono text-slate-500 text-start">
            {t("planAgencyNote")}
          </p>
        </section>
      </div>
    </main>
  );
}
