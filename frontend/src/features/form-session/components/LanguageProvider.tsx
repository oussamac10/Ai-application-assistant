"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { NextIntlClientProvider } from "next-intl";

// Import all locale translations directly
import en from "../../../../messages/en.json";
import de from "../../../../messages/de.json";
import fr from "../../../../messages/fr.json";
import ar from "../../../../messages/ar.json";
import { isRtlLanguage, UNIVERSAL_LANGUAGES } from "../utils/languages";

const messagesMap: Record<string, any> = { en, de, fr, ar };
const supportedLanguageCodes = new Set(UNIVERSAL_LANGUAGES.map((l) => l.code));
const ISO_639_1_REGEX = /^[a-z]{2}$/;

function isValidLocaleCode(code: string | null | undefined): code is string {
  if (!code) return false;
  const normalized = code.toLowerCase().trim();
  return supportedLanguageCodes.has(normalized) || ISO_639_1_REGEX.test(normalized);
}

interface LanguageContextType {
  locale: string;
  setLocale: (locale: string) => void;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<string>("en");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // Read persisted locale from localStorage
    const savedLocale = localStorage.getItem("ui-locale");
    if (isValidLocaleCode(savedLocale)) {
      setLocaleState(savedLocale.toLowerCase().trim());
    } else {
      // Try system language
      const sysLang = navigator.language.split("-")[0]?.toLowerCase();
      if (isValidLocaleCode(sysLang)) {
        setLocaleState(sysLang);
      }
    }
    setMounted(true);
  }, []);

  const setLocale = (newLocale: string) => {
    const normalized = (newLocale || "").toLowerCase().trim();
    if (isValidLocaleCode(normalized)) {
      setLocaleState(normalized);
      localStorage.setItem("ui-locale", normalized);
    }
  };

  useEffect(() => {
    if (!mounted) return;
    // Set document properties
    document.documentElement.lang = locale;
    document.documentElement.dir = isRtlLanguage(locale) ? "rtl" : "ltr";
  }, [locale, mounted]);

  // Before mount, render children directly or with default english provider to avoid SSR mismatch
  const currentMessages = messagesMap[locale] || en;

  return (
    <LanguageContext.Provider value={{ locale, setLocale }}>
      <NextIntlClientProvider locale={locale} messages={currentMessages} timeZone="UTC">
        {children}
      </NextIntlClientProvider>
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
