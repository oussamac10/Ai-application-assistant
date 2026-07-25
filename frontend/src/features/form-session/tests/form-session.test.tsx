import React from "react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  setSessionToken,
  getSessionToken,
  removeSessionToken,
  clearAllTokens,
} from "../services/sessionCredentials";
import { FieldRenderer } from "../components/FieldRenderer";
import { LanguageProvider, useLanguage } from "../components/LanguageProvider";

// Mock next-intl hooks
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: any) => {
    if (key === "progress") {
      return `Question ${values?.current} of ${values?.total} (${values?.percent}%)`;
    }
    return key;
  },
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe("sessionCredentials Storage Helper", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("should save and retrieve session tokens mapped by sessionId", () => {
    setSessionToken("session-abc", "token-123");
    expect(getSessionToken("session-abc")).toBe("token-123");
    expect(getSessionToken("session-xyz")).toBeNull();
  });

  it("should remove specific session tokens", () => {
    setSessionToken("session-abc", "token-123");
    removeSessionToken("session-abc");
    expect(getSessionToken("session-abc")).toBeNull();
  });

  it("should clear all session tokens without touching other keys", () => {
    sessionStorage.setItem("other-key", "val");
    setSessionToken("session-abc", "token-123");
    
    clearAllTokens();
    
    expect(getSessionToken("session-abc")).toBeNull();
    expect(sessionStorage.getItem("other-key")).toBe("val");
  });
});

describe("LanguageProvider Localization Component", () => {
  const TestComponent = () => {
    const { locale, setLocale } = useLanguage();
    return (
      <div>
        <span data-testid="locale-val">{locale}</span>
        <button onClick={() => setLocale("ar")}>Switch to Arabic</button>
        <button onClick={() => setLocale("de")}>Switch to German</button>
      </div>
    );
  };

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.lang = "en";
    document.documentElement.dir = "ltr";
  });

  it("should initialize default language and update HTML attributes on change", () => {
    render(
      <LanguageProvider>
        <TestComponent />
      </LanguageProvider>
    );

    // Initial state is "en"
    expect(screen.getByTestId("locale-val").textContent).toBe("en");

    // Click switch to Arabic
    fireEvent.click(screen.getByText("Switch to Arabic"));
    expect(screen.getByTestId("locale-val").textContent).toBe("ar");
    expect(document.documentElement.lang).toBe("ar");
    expect(document.documentElement.dir).toBe("rtl");

    // Click switch to German (LTR)
    fireEvent.click(screen.getByText("Switch to German"));
    expect(screen.getByTestId("locale-val").textContent).toBe("de");
    expect(document.documentElement.lang).toBe("de");
    expect(document.documentElement.dir).toBe("ltr");
  });
});

describe("FieldRenderer Component Inputs Dispatcher", () => {
  it("should render standard text input for string type", () => {
    const handleChange = vi.fn();
    render(
      <FieldRenderer
        fieldType="string"
        fieldKey="name"
        required={true}
        configuration={{}}
        options={[]}
        value="original"
        onChange={handleChange}
      />
    );

    const input = screen.getByRole("textbox") as HTMLInputElement;
    expect(input.value).toBe("original");

    fireEvent.change(input, { target: { value: "updated" } });
    expect(handleChange).toHaveBeenCalledWith("updated");
  });

  it("should render textarea with character counter for multiline_text", () => {
    const handleChange = vi.fn();
    render(
      <FieldRenderer
        fieldType="multiline_text"
        fieldKey="bio"
        required={false}
        configuration={{ maxLength: 100 }}
        options={[]}
        value="bio text"
        onChange={handleChange}
      />
    );

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    expect(textarea.value).toBe("bio text");
    expect(screen.getByText("8 / 100")).toBeDefined();
  });

  it("should render YES/NO buttons for boolean type", () => {
    const handleChange = vi.fn();
    render(
      <FieldRenderer
        fieldType="boolean"
        fieldKey="agree"
        required={true}
        configuration={{}}
        options={[]}
        value="true"
        onChange={handleChange}
      />
    );

    const yesBtn = screen.getByRole("button", { name: "Yes" });
    const noBtn = screen.getByRole("button", { name: "No" });
    
    // Yes is selected
    expect(yesBtn.className).toContain("border-indigo-500");
    
    // Click No
    fireEvent.click(noBtn);
    expect(handleChange).toHaveBeenCalledWith("false");
  });

  it("should render checklist for multiple_choice", () => {
    const handleChange = vi.fn();
    const opts = [
      { value: "a", label: "Option A" },
      { value: "b", label: "Option B" },
    ];

    render(
      <FieldRenderer
        fieldType="multiple_choice"
        fieldKey="hobbies"
        required={true}
        configuration={{}}
        options={opts}
        value='["a"]'
        onChange={handleChange}
      />
    );

    const checkboxA = screen.getByLabelText("Option A") as HTMLInputElement;
    const checkboxB = screen.getByLabelText("Option B") as HTMLInputElement;

    expect(checkboxA.checked).toBe(true);
    expect(checkboxB.checked).toBe(false);

    // Check option B
    fireEvent.click(checkboxB);
    expect(handleChange).toHaveBeenCalledWith('["a","b"]');
  });

  it("should display help text and validation error alerts when present", () => {
    render(
      <FieldRenderer
        fieldType="string"
        fieldKey="email"
        required={true}
        configuration={{}}
        options={[]}
        value=""
        onChange={vi.fn()}
        helpText="Please enter your email"
        error="Invalid email address"
      />
    );

    expect(screen.getByText("Please enter your email")).toBeDefined();
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toBe("Invalid email address");
  });
});
