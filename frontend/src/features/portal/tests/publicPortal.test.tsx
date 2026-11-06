import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CitizenDirectory } from "../components/CitizenDirectory";
import { PublicOrganizationPortal } from "../components/PublicOrganizationPortal";
import * as portalClient from "../services/portalClient";
import * as apiClient from "@/features/form-session/services/apiClient";
import { PublicOrganizationDetail, PublicOrganizationSummary } from "../types";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/organizations",
}));

let mockCurrentLocale = "en";
const mockSetLocale = vi.fn();

vi.mock("@/features/form-session/components/LanguageProvider", () => ({
  useLanguage: () => ({
    locale: mockCurrentLocale,
    setLocale: mockSetLocale,
  }),
}));

const mockSummaryOrgs: PublicOrganizationSummary[] = [
  {
    id: "org-stuttgart",
    name: "Stadtverwaltung Stuttgart — Bürgeramt",
    slug: "stadt-stuttgart",
    organization_type: "government",
    verification_status: "verified_official",
    is_verified_government: true,
    description: "Official municipal registration office of Stuttgart.",
    office_address: "Eberhardstraße 37, 70173 Stuttgart",
    official_website_url: "https://www.stuttgart.de",
    has_logo: false,
    published_forms_count: 2,
    supported_languages: ["de", "en", "tr"],
  },
  {
    id: "org-munich",
    name: "Kreisverwaltungsreferat München",
    slug: "kvr-muenchen",
    organization_type: "government",
    verification_status: "verified_official",
    is_verified_government: true,
    description: "Official municipal office of Munich.",
    office_address: "Ruppertstraße 19, 80337 München",
    official_website_url: "https://www.muenchen.de",
    has_logo: false,
    published_forms_count: 4,
    supported_languages: ["de", "en"],
  },
];

const mockDetailOrg: PublicOrganizationDetail = {
  id: "org-stuttgart",
  name: "Stadtverwaltung Stuttgart — Bürgeramt",
  slug: "stadt-stuttgart",
  organization_type: "government",
  verification_status: "verified_official",
  is_verified_government: true,
  description: "Official municipal registration office of Stuttgart.",
  office_address: "Eberhardstraße 37, 70173 Stuttgart",
  official_website_url: "https://www.stuttgart.de",
  contact_email: "buergeramt@stuttgart.de",
  has_logo: false,
  published_forms_count: 1,
  supported_languages: ["de", "en", "tr"],
  published_forms: [
    {
      id: "tpl-anmeldung",
      key: "stuttgart-anmeldung",
      name: "Anmeldung einer Wohnung (§ 17 BMG)",
      description: "Official apartment registration for Stuttgart residents.",
      category: "buergeramt",
      submission_method: "print_and_sign",
      instructions: "Please bring your ID and rental confirmation.",
      required_documents: ["Personalausweis", "Wohnungsgeberbestätigung"],
      active_version_id: "ver-anmeldung-1",
      version_number: 1,
      source_language: "de",
      supported_output_languages: ["de", "en"],
      fields_count: 14,
      has_pdf: true,
    },
  ],
};

describe("CitizenDirectory & PublicOrganizationPortal (Phase G3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders CitizenDirectory with verified public authorities and filters by keyword", async () => {
    vi.spyOn(portalClient, "listPublicOrganizations").mockResolvedValue(mockSummaryOrgs);

    render(<CitizenDirectory />);

    await waitFor(() => {
      expect(screen.getByText("Stadtverwaltung Stuttgart — Bürgeramt")).toBeInTheDocument();
      expect(screen.getByText("Kreisverwaltungsreferat München")).toBeInTheDocument();
    });

    expect(screen.getByText("Official Municipal & Government Portals")).toBeInTheDocument();
    expect(screen.getByText("2 Official Forms")).toBeInTheDocument();
    expect(screen.getByText("4 Official Forms")).toBeInTheDocument();

    // Test search filter
    const searchInput = screen.getByPlaceholderText(/Search by city, municipality/i);
    fireEvent.change(searchInput, { target: { value: "Stuttgart" } });

    expect(screen.getByText("Stadtverwaltung Stuttgart — Bürgeramt")).toBeInTheDocument();
    expect(screen.queryByText("Kreisverwaltungsreferat München")).not.toBeInTheDocument();
  });

  it("renders PublicOrganizationPortal with authority details and published forms", async () => {
    vi.spyOn(portalClient, "getPublicOrganizationBySlug").mockResolvedValue(mockDetailOrg);

    render(<PublicOrganizationPortal slug="stadt-stuttgart" />);

    await waitFor(() => {
      expect(screen.getByText("Stadtverwaltung Stuttgart — Bürgeramt")).toBeInTheDocument();
    });

    expect(screen.getByText("Verified Official Authority")).toBeInTheDocument();
    expect(screen.getByText("Anmeldung einer Wohnung (§ 17 BMG)")).toBeInTheDocument();
    expect(screen.getByText("Wohnungsgeberbestätigung")).toBeInTheDocument();
    expect(screen.getByText("100% Free for Citizens & Applicants")).toBeInTheDocument();
  });

  it("starts a free citizen intake session and redirects to guided questions", async () => {
    vi.spyOn(portalClient, "getPublicOrganizationBySlug").mockResolvedValue(mockDetailOrg);
    vi.spyOn(apiClient, "createSession").mockResolvedValue({
      publicId: "session-pub-999",
      status: "in_progress",
      ownershipToken: "token-secret-999",
      userLanguage: "en",
      outputLanguage: "de",
      expiresAt: "2026-12-01T00:00:00Z",
    });

    render(<PublicOrganizationPortal slug="stadt-stuttgart" />);

    await waitFor(() => {
      expect(screen.getByText("Anmeldung einer Wohnung (§ 17 BMG)")).toBeInTheDocument();
    });

    const startButton = screen.getByRole("button", { name: /Start in English/i });
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(apiClient.createSession).toHaveBeenCalledWith(
        "ver-anmeldung-1",
        "en",
        "de"
      );
      expect(pushMock).toHaveBeenCalledWith("/application/session/session-pub-999");
    });
  });

  it("respects active French UI locale and starts session in French", async () => {
    mockCurrentLocale = "fr";
    vi.spyOn(portalClient, "getPublicOrganizationBySlug").mockResolvedValue(mockDetailOrg);
    vi.spyOn(apiClient, "createSession").mockResolvedValue({
      publicId: "session-pub-fr-123",
      status: "in_progress",
      ownershipToken: "token-fr-123",
      userLanguage: "fr",
      outputLanguage: "de",
      expiresAt: "2026-12-01T00:00:00Z",
    });

    render(<PublicOrganizationPortal slug="stadt-stuttgart" />);

    await waitFor(() => {
      expect(screen.getByText("Anmeldung einer Wohnung (§ 17 BMG)")).toBeInTheDocument();
    });

    // The button should reflect French ("Start in Français" or native name)
    const startButton = screen.getByRole("button", { name: /Start in Français/i });
    expect(startButton).toBeInTheDocument();
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(apiClient.createSession).toHaveBeenCalledWith(
        "ver-anmeldung-1",
        "fr",
        "de"
      );
      expect(pushMock).toHaveBeenCalledWith("/application/session/session-pub-fr-123");
    });
  });
});
