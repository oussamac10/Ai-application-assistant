import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const getPublishedFormsMock = vi.fn();
const createSessionMock = vi.fn();

vi.mock("@/features/form-session/services/apiClient", () => ({
  getPublishedForms: (...args: unknown[]) => getPublishedFormsMock(...args),
  createSession: (...args: unknown[]) => createSessionMock(...args),
}));

vi.mock("@/features/form-session/services/sessionCredentials", () => ({
  setSessionToken: vi.fn(),
}));

vi.mock("@/features/document-upload/components/DocumentUploadForm", () => ({
  default: ({ currentLocale }: { currentLocale: string }) => (
    <div data-testid="document-upload-form">upload-form locale={currentLocale}</div>
  ),
}));

const PUBLISHED_FORM = {
  id: "form-1",
  templateKey: "basic-registration",
  name: "Basic Registration",
  description: "A test form",
  versionNumber: 1,
  sourceLanguage: "en",
  supportedOutputLanguages: ["en", "de", "ar"],
};

describe("Application landing — Select Manually language handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    document.documentElement.lang = "en";
    document.documentElement.dir = "ltr";
    getPublishedFormsMock.mockResolvedValue([PUBLISHED_FORM]);
  });

  async function renderLanding() {
    const { LanguageProvider } = await import(
      "@/features/form-session/components/LanguageProvider"
    );
    const { default: ApplicationLanding } = await import("@/app/application/page");
    render(
      <LanguageProvider>
        <ApplicationLanding />
      </LanguageProvider>
    );
    await waitFor(() => expect(getPublishedFormsMock).toHaveBeenCalled());
  }

  it("Select Manually: starting a session with German selected passes user_language=de", async () => {
    createSessionMock.mockResolvedValue({
      publicId: "session-1",
      ownershipToken: "token-1",
    });

    await renderLanding();

    fireEvent.click(screen.getByRole("button", { name: "tabManual" }));
    fireEvent.click(screen.getByRole("button", { name: "Deutsch" }));

    const privacyCheckbox = screen.getByRole("checkbox");
    fireEvent.click(privacyCheckbox);

    fireEvent.click(screen.getByRole("button", { name: "startSession" }));

    await waitFor(() =>
      expect(createSessionMock).toHaveBeenCalledWith("form-1", "de", "en")
    );
  });

  it("Select Manually: starting a session with Arabic selected passes user_language=ar and keeps RTL active", async () => {
    createSessionMock.mockResolvedValue({
      publicId: "session-1",
      ownershipToken: "token-1",
    });

    await renderLanding();

    fireEvent.click(screen.getByRole("button", { name: "tabManual" }));
    fireEvent.click(screen.getByRole("button", { name: "العربية" }));

    await waitFor(() =>
      expect(document.documentElement).toHaveAttribute("dir", "rtl")
    );

    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "startSession" }));

    await waitFor(() =>
      expect(createSessionMock).toHaveBeenCalledWith("form-1", "ar", "en")
    );
    expect(document.documentElement).toHaveAttribute("dir", "rtl");
  });

  it("changing the selected language before starting a session updates which language is used", async () => {
    createSessionMock.mockResolvedValue({
      publicId: "session-1",
      ownershipToken: "token-1",
    });

    await renderLanding();
    fireEvent.click(screen.getByRole("button", { name: "tabManual" }));

    // Start in English, switch to German, then submit — the session must
    // reflect the *current* selection, proving a language change before
    // starting the session is correctly picked up.
    fireEvent.click(screen.getByRole("button", { name: "English" }));
    fireEvent.click(screen.getByRole("button", { name: "Deutsch" }));
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "startSession" }));

    await waitFor(() =>
      expect(createSessionMock).toHaveBeenCalledWith("form-1", "de", "en")
    );
  });

  it("Upload Form tab behavior is unchanged by the Select Manually fix", async () => {
    await renderLanding();

    // Upload is the default tab.
    expect(screen.getByTestId("document-upload-form")).toBeDefined();
    expect(screen.getByText(/locale=en/)).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: "Deutsch" }));
    expect(screen.getByText(/locale=de/)).toBeDefined();

    // createSession (the Select Manually API) must never be called from
    // the Upload Form tab.
    expect(createSessionMock).not.toHaveBeenCalled();
  });
});
