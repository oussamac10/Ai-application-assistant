import React from "react";
import { describe, it, expect, beforeEach } from "vitest";
import { render, act } from "@testing-library/react";

import { LanguageProvider, useLanguage } from "../components/LanguageProvider";

/** Document direction must follow the *interface* language only.
 *
 * The three language concepts are independent: an Arabic form filled in an
 * English interface must stay LTR, and a German form filled in an Arabic
 * interface must be RTL. Direction keyed off the uploaded document's language
 * would flip the whole UI for a user who never asked for it. The provider
 * never receives the document's language at all, which is what makes this
 * structural rather than merely currently-true.
 */

function Switcher() {
  const { locale, setLocale } = useLanguage();
  return (
    <button
      data-testid="switch"
      data-locale={locale}
      onClick={() => setLocale("ar")}
    >
      {locale}
    </button>
  );
}

beforeEach(() => {
  localStorage.clear();
  document.documentElement.lang = "";
  document.documentElement.dir = "";
});

describe("document direction follows the interface language", () => {
  it("is LTR by default, whatever the uploaded document is", () => {
    render(
      <LanguageProvider>
        <Switcher />
      </LanguageProvider>,
    );

    expect(document.documentElement.dir).toBe("ltr");
    expect(document.documentElement.lang).toBe("en");
  });

  it("becomes RTL with lang=ar when the interface language is Arabic", () => {
    localStorage.setItem("ui-locale", "ar");

    render(
      <LanguageProvider>
        <Switcher />
      </LanguageProvider>,
    );

    expect(document.documentElement.lang).toBe("ar");
    expect(document.documentElement.dir).toBe("rtl");
  });

  it("switches to RTL when the user changes interface language at runtime", () => {
    const { getByTestId } = render(
      <LanguageProvider>
        <Switcher />
      </LanguageProvider>,
    );
    expect(document.documentElement.dir).toBe("ltr");

    act(() => {
      getByTestId("switch").click();
    });

    expect(document.documentElement.lang).toBe("ar");
    expect(document.documentElement.dir).toBe("rtl");
  });

  it("returns to LTR for a non-Arabic interface language", () => {
    localStorage.setItem("ui-locale", "de");

    render(
      <LanguageProvider>
        <Switcher />
      </LanguageProvider>,
    );

    expect(document.documentElement.lang).toBe("de");
    expect(document.documentElement.dir).toBe("ltr");
  });
});
