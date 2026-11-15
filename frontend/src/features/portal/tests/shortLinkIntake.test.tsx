import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ShortLinkIntakePage from "@/app/f/[...slug]/page";
import * as portalClient from "../services/portalClient";
import * as apiClient from "@/features/form-session/services/apiClient";
import { PublicFormDetail } from "../types";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ slug: ["stadt-stuttgart", "anmeldung"] }),
}));

vi.mock("@/features/form-session/components/LanguageProvider", () => ({
  useLanguage: () => ({
    locale: "en",
    setLocale: vi.fn(),
  }),
}));

const mockPublicForm: PublicFormDetail = {
  id: "template-form-99",
  key: "anmeldung",
  name: "Anmeldung einer Wohnung (§ 17 BMG)",
  description: "Official municipal apartment registration form.",
  category: "residence",
  submission_method: "print_and_sign",
  instructions: "Bring valid photo ID.",
  required_documents: ["Wohnungsgeberbestätigung", "Personalausweis"],
  active_version_id: "version-active-101",
  version_number: 1,
  source_language: "de",
  supported_output_languages: ["de", "en"],
  fields_count: 5,
  has_pdf: true,
  organization: {
    id: "org-stuttgart",
    name: "Stadtverwaltung Stuttgart — Bürgeramt",
    slug: "stadt-stuttgart",
    organization_type: "government",
    verification_status: "verified_official",
    is_verified_government: true,
    has_logo: false,
    published_forms_count: 3,
    supported_languages: ["de", "en"],
  },
  share_url: "http://localhost:3000/f/stadt-stuttgart/anmeldung",
  qr_svg_url: "/api/public/forms/anmeldung/qr?format=svg",
  qr_png_url: "/api/public/forms/anmeldung/qr?format=png",
  counter_poster_pdf_url: "/api/public/forms/anmeldung/counter-poster.pdf",
};

describe("ShortLinkIntakePage (/f/[...slug]) (Phase G4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form details, authority badge, and required documents", async () => {
    vi.spyOn(portalClient, "getPublicFormByIdentifier").mockResolvedValue(mockPublicForm);

    render(<ShortLinkIntakePage />);

    await waitFor(() => {
      expect(screen.getByText("Anmeldung einer Wohnung (§ 17 BMG)")).toBeInTheDocument();
    });

    expect(screen.getByText("Stadtverwaltung Stuttgart — Bürgeramt")).toBeInTheDocument();
    expect(screen.getByText("5 Questions")).toBeInTheDocument();
    expect(screen.getByText("Wohnungsgeberbestätigung")).toBeInTheDocument();
    expect(screen.getByText("Personalausweis")).toBeInTheDocument();
    expect(screen.getByText("100% Free for Citizens")).toBeInTheDocument();
  });

  it("starts a free intake session in the chosen language and navigates to guided session", async () => {
    vi.spyOn(portalClient, "getPublicFormByIdentifier").mockResolvedValue(mockPublicForm);
    vi.spyOn(apiClient, "createSession").mockResolvedValue({
      publicId: "pub-session-abc",
      status: "in_progress",
      ownershipToken: "token-secret-abc",
      userLanguage: "fr",
      outputLanguage: "de",
      expiresAt: "2026-12-01T00:00:00Z",
    });

    render(<ShortLinkIntakePage />);

    await waitFor(() => {
      expect(screen.getByText("Anmeldung einer Wohnung (§ 17 BMG)")).toBeInTheDocument();
    });

    // Select French
    const frButton = screen.getByRole("button", { name: /Français/i });
    fireEvent.click(frButton);

    const startButton = screen.getByRole("button", { name: /Start in Français/i });
    expect(startButton).toBeInTheDocument();
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(apiClient.createSession).toHaveBeenCalledWith(
        "version-active-101",
        "fr",
        "de"
      );
      expect(pushMock).toHaveBeenCalledWith("/application/session/pub-session-abc");
    });
  });

  it("displays a friendly error card when form is not found", async () => {
    vi.spyOn(portalClient, "getPublicFormByIdentifier").mockRejectedValue(
      new Error("Published form 'invalid' was not found.")
    );

    render(<ShortLinkIntakePage />);

    await waitFor(() => {
      expect(screen.getByText("Form Not Available")).toBeInTheDocument();
      expect(screen.getByText(/Published form 'invalid' was not found/i)).toBeInTheDocument();
    });
  });
});
