export interface LanguageOption {
  /** ISO 639-1 two-letter language code */
  code: string;
  /** Native language name (endonym) */
  nativeName: string;
  /** English name for searchability */
  englishName: string;
  /** Writing direction */
  dir: "ltr" | "rtl";
  /** Geographic/linguistic grouping for browsing */
  region: "Popular" | "Europe" | "Middle East & Africa" | "Asia & Americas";
  /** Whether static UI chrome translations exist in messages/*.json */
  hasStaticUiBundle?: boolean;
}

/**
 * Universal flag-free language catalog (ISO 639-1).
 * Never uses country flags to represent languages.
 */
export const UNIVERSAL_LANGUAGES: LanguageOption[] = [
  // Core languages with full static UI bundles + AI support
  {
    code: "en",
    nativeName: "English",
    englishName: "English",
    dir: "ltr",
    region: "Popular",
    hasStaticUiBundle: true,
  },
  {
    code: "de",
    nativeName: "Deutsch",
    englishName: "German",
    dir: "ltr",
    region: "Popular",
    hasStaticUiBundle: true,
  },
  {
    code: "fr",
    nativeName: "Français",
    englishName: "French",
    dir: "ltr",
    region: "Popular",
    hasStaticUiBundle: true,
  },
  {
    code: "ar",
    nativeName: "العربية",
    englishName: "Arabic",
    dir: "rtl",
    region: "Popular",
    hasStaticUiBundle: true,
  },

  // High-demand migration, civic & global languages
  {
    code: "es",
    nativeName: "Español",
    englishName: "Spanish",
    dir: "ltr",
    region: "Popular",
  },
  {
    code: "tr",
    nativeName: "Türkçe",
    englishName: "Turkish",
    dir: "ltr",
    region: "Popular",
  },
  {
    code: "uk",
    nativeName: "Українська",
    englishName: "Ukrainian",
    dir: "ltr",
    region: "Popular",
  },
  {
    code: "ru",
    nativeName: "Русский",
    englishName: "Russian",
    dir: "ltr",
    region: "Popular",
  },
  {
    code: "fa",
    nativeName: "فارسی",
    englishName: "Persian (Farsi)",
    dir: "rtl",
    region: "Middle East & Africa",
  },
  {
    code: "ur",
    nativeName: "اردو",
    englishName: "Urdu",
    dir: "rtl",
    region: "Asia & Americas",
  },
  {
    code: "ku",
    nativeName: "Kurdî",
    englishName: "Kurdish",
    dir: "ltr",
    region: "Middle East & Africa",
  },
  {
    code: "ps",
    nativeName: "پښتو",
    englishName: "Pashto",
    dir: "rtl",
    region: "Asia & Americas",
  },
  {
    code: "pl",
    nativeName: "Polski",
    englishName: "Polish",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "ro",
    nativeName: "Română",
    englishName: "Romanian",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "it",
    nativeName: "Italiano",
    englishName: "Italian",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "pt",
    nativeName: "Português",
    englishName: "Portuguese",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "nl",
    nativeName: "Nederlands",
    englishName: "Dutch",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "el",
    nativeName: "Ελληνικά",
    englishName: "Greek",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "bg",
    nativeName: "Български",
    englishName: "Bulgarian",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "sr",
    nativeName: "Српски",
    englishName: "Serbian",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "hr",
    nativeName: "Hrvatski",
    englishName: "Croatian",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "sq",
    nativeName: "Shqip",
    englishName: "Albanian",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "cs",
    nativeName: "Čeština",
    englishName: "Czech",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "hu",
    nativeName: "Magyar",
    englishName: "Hungarian",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "sv",
    nativeName: "Svenska",
    englishName: "Swedish",
    dir: "ltr",
    region: "Europe",
  },
  {
    code: "so",
    nativeName: "Soomaali",
    englishName: "Somali",
    dir: "ltr",
    region: "Middle East & Africa",
  },
  {
    code: "ti",
    nativeName: "ትግርኛ",
    englishName: "Tigrinya",
    dir: "ltr",
    region: "Middle East & Africa",
  },
  {
    code: "am",
    nativeName: "አማርኛ",
    englishName: "Amharic",
    dir: "ltr",
    region: "Middle East & Africa",
  },
  {
    code: "sw",
    nativeName: "Kiswahili",
    englishName: "Swahili",
    dir: "ltr",
    region: "Middle East & Africa",
  },
  {
    code: "ha",
    nativeName: "Hausa",
    englishName: "Hausa",
    dir: "ltr",
    region: "Middle East & Africa",
  },
  {
    code: "he",
    nativeName: "עברית",
    englishName: "Hebrew",
    dir: "rtl",
    region: "Middle East & Africa",
  },
  {
    code: "hi",
    nativeName: "हिन्दी",
    englishName: "Hindi",
    dir: "ltr",
    region: "Asia & Americas",
  },
  {
    code: "bn",
    nativeName: "বাংলা",
    englishName: "Bengali",
    dir: "ltr",
    region: "Asia & Americas",
  },
  {
    code: "ta",
    nativeName: "தமிழ்",
    englishName: "Tamil",
    dir: "ltr",
    region: "Asia & Americas",
  },
  {
    code: "vi",
    nativeName: "Tiếng Việt",
    englishName: "Vietnamese",
    dir: "ltr",
    region: "Asia & Americas",
  },
  {
    code: "zh",
    nativeName: "中文",
    englishName: "Chinese",
    dir: "ltr",
    region: "Asia & Americas",
  },
  {
    code: "id",
    nativeName: "Bahasa Indonesia",
    englishName: "Indonesian",
    dir: "ltr",
    region: "Asia & Americas",
  },
  {
    code: "tl",
    nativeName: "Tagalog",
    englishName: "Filipino / Tagalog",
    dir: "ltr",
    region: "Asia & Americas",
  },
  {
    code: "ko",
    nativeName: "한국어",
    englishName: "Korean",
    dir: "ltr",
    region: "Asia & Americas",
  },
  {
    code: "ja",
    nativeName: "日本語",
    englishName: "Japanese",
    dir: "ltr",
    region: "Asia & Americas",
  },
];

export const POPULAR_LANGUAGE_CODES = [
  "en",
  "de",
  "fr",
  "ar",
  "es",
  "tr",
  "uk",
  "fa",
] as const;

export const RTL_LANGUAGE_CODES = new Set(
  UNIVERSAL_LANGUAGES.filter((l) => l.dir === "rtl").map((l) => l.code),
);

export function isRtlLanguage(code: string): boolean {
  return RTL_LANGUAGE_CODES.has((code || "").toLowerCase().trim());
}

export function getLanguageByCode(code: string): LanguageOption {
  const normalized = (code || "en").toLowerCase().trim();
  const found = UNIVERSAL_LANGUAGES.find((l) => l.code === normalized);
  if (found) return found;
  return {
    code: normalized,
    nativeName: normalized.toUpperCase(),
    englishName: normalized.toUpperCase(),
    dir: isRtlLanguage(normalized) ? "rtl" : "ltr",
    region: "Europe",
  };
}
