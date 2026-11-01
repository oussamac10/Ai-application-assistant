import React from "react";
import { render, screen, act, fireEvent } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { useTranslations } from "next-intl";

import en from "../../../../messages/en.json";
import de from "../../../../messages/de.json";
import fr from "../../../../messages/fr.json";
import ar from "../../../../messages/ar.json";
import tr from "../../../../messages/tr.json";
import uk from "../../../../messages/uk.json";
import es from "../../../../messages/es.json";
import ru from "../../../../messages/ru.json";

import { LanguageProvider, useLanguage } from "../components/LanguageProvider";
import { UNIVERSAL_LANGUAGES } from "../utils/languages";

function flattenMessages(
  obj: Record<string, unknown>,
  prefix = "",
): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      Object.assign(result, flattenMessages(value as Record<string, unknown>, path));
    } else {
      result[path] = String(value ?? "");
    }
  }
  return result;
}

function extractPlaceholders(text: string): string[] {
  const matches = text.match(/\{[a-zA-Z0-9_]+\}/g) || [];
  return Array.from(new Set(matches)).sort();
}

function ProbeComponent() {
  const { locale, setLocale } = useLanguage();
  const tHome = useTranslations("home");
  const tNav = useTranslations("nav");
  return (
    <div>
      <span data-testid="active-locale">{locale}</span>
      <h1 data-testid="home-headline">{tHome("headline")}</h1>
      <span data-testid="nav-new-app">{tNav("newApplication")}</span>
      <button type="button" onClick={() => setLocale("tr")}>
        switch-tr
      </button>
      <button type="button" onClick={() => setLocale("uk")}>
        switch-uk
      </button>
      <button type="button" onClick={() => setLocale("es")}>
        switch-es
      </button>
      <button type="button" onClick={() => setLocale("ru")}>
        switch-ru
      </button>
      <button type="button" onClick={() => setLocale("ar")}>
        switch-ar
      </button>
      <button type="button" onClick={() => setLocale("en")}>
        switch-en
      </button>
    </div>
  );
}

describe("Phase S3 — 8 Full UI Languages Parity & Switching", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.lang = "en";
    document.documentElement.dir = "ltr";
  });

  it("maintains 100% key and ICU placeholder parity across en, de, fr, ar, tr, uk, es, ru", () => {
    const bundles: Record<string, Record<string, unknown>> = {
      en,
      de,
      fr,
      ar,
      tr,
      uk,
      es,
      ru,
    };
    const baseFlat = flattenMessages(en);
    const baseKeys = Object.keys(baseFlat).sort();

    // Ensure Phase S3 namespaces exist
    expect(baseKeys.some((k) => k.startsWith("home."))).toBe(true);
    expect(baseKeys.some((k) => k.startsWith("nav."))).toBe(true);
    expect(baseKeys.some((k) => k.startsWith("setup."))).toBe(true);
    expect(baseKeys.some((k) => k.startsWith("footer."))).toBe(true);

    for (const [locale, bundle] of Object.entries(bundles)) {
      const flat = flattenMessages(bundle);
      const keys = Object.keys(flat).sort();
      expect(keys, `Key mismatch in ${locale}.json`).toEqual(baseKeys);

      for (const key of baseKeys) {
        expect(flat[key].trim().length, `Empty value for ${locale}:${key}`).toBeGreaterThan(0);
        expect(
          extractPlaceholders(flat[key]),
          `ICU placeholder mismatch in ${locale}:${key}`,
        ).toEqual(extractPlaceholders(baseFlat[key]));
      }
    }
  });

  it("marks all 8 launch locales with hasStaticUiBundle in UNIVERSAL_LANGUAGES", () => {
    const required = ["en", "de", "fr", "ar", "tr", "uk", "es", "ru"];
    for (const code of required) {
      const entry = UNIVERSAL_LANGUAGES.find((l) => l.code === code);
      expect(entry, `Missing language ${code}`).toBeDefined();
      expect(entry?.hasStaticUiBundle, `${code} missing hasStaticUiBundle`).toBe(true);
    }
  });

  it("switches UI messages across tr, uk, es, ru, and ar without falling back to English", async () => {
    await act(async () => {
      render(
        <LanguageProvider>
          <ProbeComponent />
        </LanguageProvider>,
      );
    });

    const englishHeadline = screen.getByTestId("home-headline").textContent;

    for (const code of ["tr", "uk", "es", "ru", "ar"]) {
      await act(async () => {
        fireEvent.click(screen.getByText(`switch-${code}`));
      });
      expect(screen.getByTestId("active-locale").textContent).toBe(code);
      expect(screen.getByTestId("home-headline").textContent).not.toBe(englishHeadline);
      expect(document.documentElement.dir).toBe(code === "ar" ? "rtl" : "ltr");
      expect(document.documentElement.lang).toBe(code);
    }

    await act(async () => {
      fireEvent.click(screen.getByText("switch-en"));
    });
    expect(document.documentElement.dir).toBe("ltr");
    expect(document.documentElement.lang).toBe("en");
  });
});
