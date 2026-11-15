import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PortalDashboard } from "../components/PortalDashboard";
import { CandidateIntakeLanding } from "../components/CandidateIntakeLanding";
import * as portalClient from "../services/portalClient";
import * as apiClient from "@/features/form-session/services/apiClient";
import { Case, Organization, OrganizationFormSummary } from "../types";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ token: "mock-invite-token-123" }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/features/form-session/components/LanguageProvider", () => ({
  useLanguage: () => ({
    locale: "en",
    setLocale: vi.fn(),
  }),
}));

const mockOrg: Organization = {
  id: "org-1",
  name: "Munich Relocation Services GmbH",
  slug: "munich-relocation",
  billing_plan: "agency_pro",
  allowed_cases_per_month: 50,
  role: "owner",
  created_at: "2026-11-01T00:00:00Z",
  verification_status: "verified_official",
  is_verified_government: true,
  supported_languages: ["en", "de"],
};

const mockCases: Case[] = [
  {
    id: "case-1",
    public_id: "case-pub-1",
    organization_id: "org-1",
    candidate_name: "Dr. Sarah Connor",
    candidate_email: "sarah.connor@cyberdyne.org",
    status: "in_progress",
    form_version_id: "ver-aufenthalt-1",
    form_title: "Antrag auf Erteilung eines Aufenthaltstitels",
    session_public_id: "sess-123",
    notes: "Fast-track Blue Card candidate",
    created_at: "2026-11-01T01:00:00Z",
    updated_at: "2026-11-01T01:00:00Z",
    invite_token: "token-abc-123",
    total_fields: 12,
    answered_fields: 6,
    progress_percent: 50,
  },
  {
    id: "case-2",
    public_id: "case-pub-2",
    organization_id: "org-1",
    candidate_name: "John Matrix",
    candidate_email: "matrix@commando.org",
    status: "awaiting_review",
    form_version_id: "ver-anmeldung-1",
    form_title: "Anmeldung bei der Meldebehörde",
    session_public_id: "sess-456",
    notes: "Munich residence registration",
    created_at: "2026-11-01T00:30:00Z",
    updated_at: "2026-11-01T00:45:00Z",
    total_fields: 10,
    answered_fields: 10,
    progress_percent: 100,
  },
];

const mockForms: OrganizationFormSummary[] = [
  {
    id: "tpl-1",
    key: "de-anmeldung",
    name: "Wohnungsgeberbestätigung",
    category: "residence",
    submissionMethod: "online",
    requiredDocuments: [],
    hasPdf: true,
    status: "published",
    versionNumber: 1,
    fieldsCount: 8,
    createdAt: "2026-11-01T00:00:00Z",
    updatedAt: "2026-11-01T00:00:00Z",
  },
  {
    id: "tpl-2",
    key: "de-kindergeld",
    name: "Antrag auf Kindergeld",
    category: "family",
    submissionMethod: "online",
    requiredDocuments: [],
    hasPdf: true,
    status: "needs_review",
    versionNumber: 1,
    fieldsCount: 14,
    createdAt: "2026-11-01T00:00:00Z",
    updatedAt: "2026-11-01T00:00:00Z",
  },
];

describe("B2B & B2G Platform — Portal & Case Management", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders workspace details, metrics, and official forms in PortalDashboard", async () => {
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listOrganizationForms").mockResolvedValue(mockForms);

    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Munich Relocation Services GmbH")).toBeDefined();
    });

    expect(screen.getByText("Total forms")).toBeDefined();
    expect(screen.getByText("Live in portal")).toBeDefined();
    expect(screen.getAllByText("Needs review").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Wohnungsgeberbestätigung")).toBeDefined();
    expect(screen.getByText("Antrag auf Kindergeld")).toBeDefined();
  });

  it("filters forms in table when searching by form name", async () => {
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listOrganizationForms").mockResolvedValue(mockForms);

    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Wohnungsgeberbestätigung")).toBeDefined();
    });

    const searchInput = screen.getByPlaceholderText("Search forms...");
    fireEvent.change(searchInput, { target: { value: "Kindergeld" } });

    await waitFor(() => {
      expect(screen.queryByText("Wohnungsgeberbestätigung")).toBeNull();
      expect(screen.getByText("Antrag auf Kindergeld")).toBeDefined();
    });
  });

  it("opens upload form modal on clicking Upload PDF", async () => {
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listOrganizationForms").mockResolvedValue([]);

    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Munich Relocation Services GmbH")).toBeDefined();
    });

    const uploadBtns = screen.getAllByRole("button", { name: /Upload PDF/i });
    fireEvent.click(uploadBtns[0]);

    await waitFor(() => {
      expect(screen.getByText("Upload PDF Form")).toBeDefined();
    });
  });

  it("handles candidate email OTP inspection, branding, checklist, verification, and intake launch", async () => {
    sessionStorage.clear();

    const inspectSpy = vi
      .spyOn(portalClient, "inspectCandidateInvite")
      .mockResolvedValue({
        case_public_id: "pub-case-789",
        candidate_name: "Alexey Naval",
        masked_email: "a***@example.com",
        form_title: "Antrag auf Erteilung eines Aufenthaltstitels",
        form_description: "Residence permit application",
        form_version_id: "ver-aufenthalt-1",
        user_language: "uk",
        source_language: "de",
        status: "invited",
        otp_verified: false,
        required_documents: ["Valid passport", "Signed rental lease"],
        submission_method: "in_person",
        instructions: "Bring original passport to the appointment.",
        organization: {
          id: "org-99",
          name: "Berlin Global Mobility GmbH",
          slug: "berlin-global-mobility",
          organization_type: "business",
          verification_status: "verified_official",
          is_verified_government: true,
          description: "International talent relocation desk",
          has_logo: true,
          office_address: "Friedrichstr. 110, Berlin",
          contact_email: "care@berlin-mobility.example",
          contact_phone: "+49 30 900123",
          official_website_url: "https://berlin-mobility.example",
          ui_theme_config: { primary_color: "#10b981" },
        },
      });

    const sendOtpSpy = vi
      .spyOn(portalClient, "sendCandidateInviteOtp")
      .mockResolvedValue({
        sent: true,
        masked_email: "a***@example.com",
        expires_in_seconds: 600,
      });

    const verifyOtpSpy = vi
      .spyOn(portalClient, "verifyCandidateInviteOtp")
      .mockResolvedValue({
        session_id: "sess-abc-789",
        session_token: "raw-token-12345",
        case_public_id: "pub-case-789",
        candidate_name: "Alexey Naval",
        candidate_email: "alexey@example.com",
        form_title: "Antrag auf Erteilung eines Aufenthaltstitels",
        form_version_id: "ver-aufenthalt-1",
        user_language: "uk",
        source_language: "de",
        status: "in_progress",
      });

    render(<CandidateIntakeLanding token="valid-token-123" />);

    await waitFor(() => {
      expect(screen.getByText("Alexey Naval")).toBeDefined();
      expect(
        screen.getAllByText("Berlin Global Mobility GmbH").length
      ).toBeGreaterThanOrEqual(1);
    });

    expect(inspectSpy).toHaveBeenCalledWith("valid-token-123");
    expect(screen.getByText("Friedrichstr. 110, Berlin")).toBeDefined();
    expect(screen.getByText("care@berlin-mobility.example")).toBeDefined();
    expect(screen.getByTestId("invite-required-documents")).toBeDefined();
    expect(screen.getByText("Valid passport")).toBeDefined();
    expect(screen.getByText("a***@example.com")).toBeDefined();

    // Form start is gated until email OTP verification succeeds
    expect(screen.queryByText("startAssistedSession")).toBeNull();

    fireEvent.click(screen.getByTestId("send-invite-otp-btn"));
    await waitFor(() => {
      expect(sendOtpSpy).toHaveBeenCalledWith("valid-token-123");
      expect(screen.getByTestId("invite-otp-input")).toBeDefined();
    });

    fireEvent.change(screen.getByTestId("invite-otp-input"), {
      target: { value: "654321" },
    });
    fireEvent.click(screen.getByTestId("verify-invite-otp-btn"));

    await waitFor(() => {
      expect(verifyOtpSpy).toHaveBeenCalledWith("valid-token-123", "654321");
      expect(screen.getByText("startAssistedSession")).toBeDefined();
    });

    // Candidate clicks start application
    fireEvent.click(screen.getByText("startAssistedSession"));

    expect(sessionStorage.getItem("session-token:sess-abc-789")).toBe(
      "raw-token-12345"
    );
    expect(pushMock).toHaveBeenCalledWith("/application/session/sess-abc-789");
  });

  it("renders expired or invalid error message on invalid candidate token", async () => {
    vi.spyOn(portalClient, "inspectCandidateInvite").mockRejectedValue(
      new Error("Invalid or expired candidate invite link.")
    );

    render(<CandidateIntakeLanding token="expired-token" />);

    await waitFor(() => {
      expect(screen.getByText(/Invite Link Expired or Invalid/i)).toBeDefined();
      expect(screen.getByText(/Invalid or expired candidate invite link/i)).toBeDefined();
    });
  });

  it("manages candidate invites in PortalDashboard with resend and revoke actions", async () => {
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listOrganizationForms").mockResolvedValue(mockForms);
    vi.spyOn(portalClient, "listCases").mockResolvedValue(mockCases);

    const resentCase: Case = {
      ...mockCases[0],
      invite_token: "rotated-invite-token-999",
      resend_count: 1,
    };
    const revokedCase: Case = {
      ...mockCases[0],
      status: "revoked",
      revoked_at: "2026-11-15T12:00:00Z",
    };

    const resendSpy = vi
      .spyOn(portalClient, "resendCaseInvite")
      .mockResolvedValue(resentCase);
    const revokeSpy = vi
      .spyOn(portalClient, "revokeCaseInvite")
      .mockResolvedValue(revokedCase);

    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId("portal-tab-cases")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("portal-tab-cases"));

    await waitFor(() => {
      expect(screen.getByTestId("portal-cases-workspace")).toBeDefined();
      expect(screen.getByText("Dr. Sarah Connor")).toBeDefined();
    });

    // Resend rotated invite link -> opens InviteSuccessModal
    fireEvent.click(screen.getByTestId("resend-case-case-pub-1"));
    await waitFor(() => {
      expect(resendSpy).toHaveBeenCalledWith("case-pub-1");
      expect(screen.getByText("inviteModalTitle")).toBeDefined();
    });

    fireEvent.click(screen.getByText("done"));

    // Revoke invite link -> marks status Revoked
    fireEvent.click(screen.getByTestId("revoke-case-case-pub-1"));
    await waitFor(() => {
      expect(revokeSpy).toHaveBeenCalledWith("case-pub-1");
    });

    const row = screen.getByTestId("case-row-case-pub-1");
    expect(row.textContent).toContain("Revoked");
  });

  it("applies authority ui_theme_config hiding metrics strip and showing custom notice banner", async () => {
    const themedOrg: Organization = {
      ...mockOrg,
      ui_theme_config: {
        primary_color: "#FEDB00",
        accent_color: "#1E3A8A",
        sidebar_theme: "heraldic",
        layout_density: "compact",
        show_metrics_strip: false,
        show_authority_metadata: true,
        show_portal_link: false,
        section_order: ["header", "actions", "forms"],
        citizen_welcome_heading: "Willkommen beim Amt",
        citizen_notice_banner: "Wartungsarbeiten am System am Wochenende",
      },
    };

    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(themedOrg);
    vi.spyOn(portalClient, "listOrganizationForms").mockResolvedValue(mockForms);

    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Munich Relocation Services GmbH")).toBeDefined();
    });

    // Custom notice banner is rendered
    expect(screen.getByText("Wartungsarbeiten am System am Wochenende")).toBeDefined();

    // Metrics strip is hidden
    expect(screen.queryByText("Total forms")).toBeNull();
    expect(screen.queryByText("Live in portal")).toBeNull();

    // Forms and actions are still rendered
    expect(screen.getByText("Wohnungsgeberbestätigung")).toBeDefined();
  });
});
