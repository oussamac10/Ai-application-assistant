import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Home from "./page";
import { LanguageProvider } from "@/features/form-session/components/LanguageProvider";
import {
  getPublishedForms,
  createSession,
} from "@/features/form-session/services/apiClient";
import { getSessionToken } from "@/features/form-session/services/sessionCredentials";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/features/form-session/services/apiClient", async () => {
  const actual = await vi.importActual<
    typeof import("@/features/form-session/services/apiClient")
  >("@/features/form-session/services/apiClient");
  return {
    ...actual,
    getPublishedForms: vi.fn(),
    createSession: vi.fn(),
  };
});

const SAMPLE_FORMS = [
  {
    id: "ver-anmeldung-1",
    templateKey: "de-anmeldung",
    name: "Anmeldung bei der Meldebehörde",
    description: "Municipal address registration in Germany (§ 17 BMG).",
    versionNumber: 1,
    sourceLanguage: "de",
    supportedOutputLanguages: ["de"],
  },
  {
    id: "ver-kg1-1",
    templateKey: "de-kindergeld-kg1",
    name: "Antrag auf Kindergeld (KG1)",
    description: "Child benefit application for families in Germany.",
    versionNumber: 1,
    sourceLanguage: "de",
    supportedOutputLanguages: ["de"],
  },
];

describe("Phase S3 — Conversion Homepage & 1-Click German Form Launchers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    document.documentElement.lang = "en";
    document.documentElement.dir = "ltr";
  });

  function renderHome() {
    return render(
      <LanguageProvider>
        <Home />
      </LanguageProvider>,
    );
  }

  it("renders the conversion hero, upload CTA, RDG/GDPR trust pillars, and pricing preview without developer telemetry", async () => {
    vi.mocked(getPublishedForms).mockResolvedValue(SAMPLE_FORMS);

    renderHome();

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /Multilingual form completion infrastructure/i,
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Phase 1 Monorepo Foundation/i)).toBeNull();
    expect(screen.queryByText(/PostgreSQL/i)).toBeNull();

    const uploadLinks = screen.getAllByRole("link", {
      name: /Launch Form Assistant/i,
    });
    expect(uploadLinks[0]).toHaveAttribute("href", "/application");

    expect(await screen.findByText("Anmeldung bei der Meldebehörde")).toBeInTheDocument();
    expect(screen.getByText(/Enterprise & Public Sector/i)).toBeInTheDocument();
    expect(screen.getByText(/Administrative & Language Tool — Not Legal Advice/i)).toBeInTheDocument();
  });

  it("launches a zero-signup 1-click guided session in the user's selected UI language", async () => {
    vi.mocked(getPublishedForms).mockResolvedValue(SAMPLE_FORMS);
    vi.mocked(createSession).mockResolvedValue({
      publicId: "sess-quick-123",
      status: "session_created",
      ownershipToken: "tok-secret-xyz",
      userLanguage: "tr",
      outputLanguage: "de",
      expiresAt: "2026-10-27T23:00:00Z",
    });

    renderHome();

    expect(await screen.findByText("Anmeldung bei der Meldebehörde")).toBeInTheDocument();

    // Switch interface language directly from the hero language bar to Turkish
    fireEvent.click(screen.getByRole("button", { name: /Türkçe/i }));

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: /Relocation ajansları ve kamu kurumları için küresel çok dilli form doldurma altyapısı/i,
      }),
    ).toBeInTheDocument();

    // Click the 1-click launcher for Anmeldung
    const launchBtn = screen.getByTestId("quick-launch-de-anmeldung");
    fireEvent.click(launchBtn);

    await waitFor(() => {
      expect(createSession).toHaveBeenCalledWith("ver-anmeldung-1", "tr", "de");
    });
    expect(getSessionToken("sess-quick-123")).toBe("tok-secret-xyz");
    expect(pushMock).toHaveBeenCalledWith("/application/session/sess-quick-123");
  });

  it("renders gracefully with upload fallback when published forms request fails", async () => {
    vi.mocked(getPublishedForms).mockRejectedValue(new Error("unavailable"));

    renderHome();

    await waitFor(() => {
      expect(getPublishedForms).toHaveBeenCalledTimes(1);
    });

    // Upload CTA remains accessible even if catalog fetch fails
    expect(
      screen.getAllByRole("link", { name: /Launch Form Assistant/i })[0],
    ).toHaveAttribute("href", "/application");
  });
});
