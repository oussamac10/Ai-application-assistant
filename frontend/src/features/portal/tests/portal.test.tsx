import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PortalDashboard } from "../components/PortalDashboard";
import { CandidateIntakeLanding } from "../components/CandidateIntakeLanding";
import * as portalClient from "../services/portalClient";
import * as apiClient from "@/features/form-session/services/apiClient";
import { Case, Organization } from "../types";

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

describe("B2B & B2G Platform — Portal & Case Management", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(portalClient, "getSubscription").mockResolvedValue({
      id: "sub-1",
      organization_id: "org-1",
      plan_key: "agency_pro",
      status: "active",
      monthly_case_limit: 50,
      cases_used_this_period: 2,
      remaining_cases: 48,
      cancel_at_period_end: false,
    });
  });

  it("renders workspace details, metrics, and case table in PortalDashboard", async () => {
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listCases").mockResolvedValue(mockCases);

    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Munich Relocation Services GmbH")).toBeDefined();
    });

    expect(screen.getAllByText(/Agency Pro/)[0]).toBeDefined();
    expect(screen.getByText(/48 cases remaining/)).toBeDefined();
    expect(screen.getByText("Manage Billing & Invoices")).toBeDefined();
    expect(screen.getByText("Dr. Sarah Connor")).toBeDefined();
    expect(screen.getByText("sarah.connor@cyberdyne.org")).toBeDefined();
    expect(screen.getByText("John Matrix")).toBeDefined();
    expect(screen.getByText("50%")).toBeDefined();
    expect(screen.getByText("100%")).toBeDefined();
  });

  it("filters cases in table when searching by candidate name", async () => {
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listCases").mockResolvedValue(mockCases);

    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Dr. Sarah Connor")).toBeDefined();
    });

    const searchInput = screen.getByPlaceholderText("searchPlaceholder");
    fireEvent.change(searchInput, { target: { value: "Matrix" } });

    await waitFor(() => {
      expect(screen.queryByText("Dr. Sarah Connor")).toBeNull();
      expect(screen.getByText("John Matrix")).toBeDefined();
    });
  });

  it("creates a candidate case via NewCaseModal", async () => {
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listCases").mockResolvedValue([]);
    vi.spyOn(apiClient, "getPublishedForms").mockResolvedValue([
      {
        id: "ver-aufenthalt-1",
        name: "Antrag auf Aufenthaltstitel",
        templateKey: "de-aufenthaltstitel",
        description: "Official residence permit",
        versionNumber: 1,
        sourceLanguage: "de",
        supportedOutputLanguages: ["de"],
      },
    ]);
    const createCaseSpy = vi.spyOn(portalClient, "createCase").mockResolvedValue({
      id: "case-new",
      public_id: "pub-new",
      organization_id: "org-1",
      candidate_name: "Elena Rostova",
      candidate_email: "elena@example.com",
      status: "invited",
      form_version_id: "ver-aufenthalt-1",
      form_title: "Antrag auf Aufenthaltstitel",
      created_at: "2026-11-01T01:30:00Z",
      updated_at: "2026-11-01T01:30:00Z",
      invite_token: "new-invite-token-xyz",
      total_fields: 12,
      answered_fields: 0,
      progress_percent: 0,
    });

    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Munich Relocation Services GmbH")).toBeDefined();
    });

    // Open New Case Modal
    const newCaseBtn = screen.getAllByRole("button", { name: /newCase/i })[0];
    fireEvent.click(newCaseBtn);

    await waitFor(() => {
      expect(screen.getByText("modalTitle")).toBeDefined();
    });

    // Fill candidate name & email
    fireEvent.change(screen.getByPlaceholderText("candidateNamePlaceholder"), {
      target: { value: "Elena Rostova" },
    });
    fireEvent.change(screen.getByPlaceholderText("candidateEmailPlaceholder"), {
      target: { value: "elena@example.com" },
    });

    // Submit form
    const submitBtn = screen.getByRole("button", { name: /createButton/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createCaseSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          candidate_name: "Elena Rostova",
          candidate_email: "elena@example.com",
          form_version_id: "ver-aufenthalt-1",
        })
      );
    });
  });

  it("handles candidate magic-link redemption and intake landing", async () => {
    vi.spyOn(portalClient, "redeemCandidateInvite").mockResolvedValue({
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
      expect(screen.getByText("Antrag auf Erteilung eines Aufenthaltstitels")).toBeDefined();
    });

    // Candidate clicks start application
    const startBtn = screen.getByText("startAssistedSession");
    fireEvent.click(startBtn);

    expect(pushMock).toHaveBeenCalledWith("/application/session/sess-abc-789");
  });

  it("renders expired or invalid error message on invalid candidate token", async () => {
    vi.spyOn(portalClient, "redeemCandidateInvite").mockRejectedValue(
      new Error("Invalid or expired candidate invite link.")
    );

    render(<CandidateIntakeLanding token="expired-token" />);

    await waitFor(() => {
      expect(screen.getByText(/Invite Link Expired or Invalid/i)).toBeDefined();
      expect(screen.getByText(/Invalid or expired candidate invite link/i)).toBeDefined();
    });
  });
});
