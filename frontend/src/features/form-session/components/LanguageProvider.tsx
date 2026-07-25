"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { NextIntlClientProvider } from "next-intl";

// Import all locale translations directly
import en from "../../../../messages/en.json";
import de from "../../../../messages/de.json";
import fr from "../../../../messages/fr.json";
import ar from "../../../../messages/ar.json";

const messagesMap: Record<string, any> = { en, de, fr, ar };

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
    if (savedLocale && ["en", "de", "fr", "ar"].includes(savedLocale)) {
      setLocaleState(savedLocale);
    } else {
      // Try system language
      const sysLang = navigator.language.split("-")[0];
      if (["en", "de", "fr", "ar"].includes(sysLang)) {
        setLocaleState(sysLang);
      }
    }
    setMounted(true);
  }, []);

  const setLocale = (newLocale: string) => {
    if (["en", "de", "fr", "ar"].includes(newLocale)) {
      setLocaleState(newLocale);
      localStorage.setItem("ui-locale", newLocale);
    }
  };

  useEffect(() => {
    if (!mounted) return;
    // Set document properties
    document.documentElement.lang = locale;
    document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";
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
