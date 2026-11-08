import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FormSchemaReviewStudio } from "../components/FormSchemaReviewStudio";
import { PublicOrganizationPortal } from "../components/PublicOrganizationPortal";
import * as portalClient from "../services/portalClient";
import {
  FormReviewDetail,
  Organization,
  AutoMapResponse,
  PublicOrganizationDetail,
  FormSemanticSearchResult,
} from "../types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => "/organizations/stuttgart",
}));

vi.mock("@/features/form-session/components/LanguageProvider", () => ({
  useLanguage: () => ({
    locale: "en",
    setLocale: vi.fn(),
  }),
}));

const mockOrg: Organization = {
  id: "org-1",
  name: "Stadtverwaltung Stuttgart",
  slug: "stuttgart",
  billing_plan: "enterprise",
  allowed_cases_per_month: 500,
  role: "owner",
  verification_status: "verified",
  is_verified_government: true,
  supported_languages: ["de", "en", "ar", "fr"],
  created_at: new Date().toISOString(),
};

const mockReview: FormReviewDetail = {
  templateId: "tmpl-1",
  versionId: "ver-1",
  key: "anmeldung_wohnung",
  name: "Anmeldung einer Wohnung",
  category: "wohnen",
  submissionMethod: "print_and_sign",
  status: "needs_review",
  versionNumber: 1,
  sourceLanguage: "de",
  pageCount: 1,
  requiredDocuments: [],
  fields: [
    {
      id: "f-vorname",
      key: "vorname_antragsteller",
      fieldType: "string",
      required: true,
      requiredness: "required",
      position: 0,
      configuration: { page: 1, bbox: [50, 100, 200, 120] },
      questionKey: null,
      translations: [
        {
          language: "de",
          label: "Vorname",
        },
      ],
      options: [],
    },
    {
      id: "f-geburtsdatum",
      key: "geburtsdatum",
      fieldType: "date",
      required: true,
      requiredness: "required",
      position: 1,
      configuration: { page: 1, bbox: [50, 130, 200, 150] },
      questionKey: null,
      translations: [
        {
          language: "de",
          label: "Geburtsdatum",
        },
      ],
      options: [],
    },
  ],
};

const mockAutoMapResponse: AutoMapResponse = {
  template_id: "tmpl-1",
  total_fields: 2,
  mapped_fields_count: 2,
  suggestions: [
    {
      field_id: "f-vorname",
      field_key: "vorname_antragsteller",
      field_label: "Vorname",
      current_question_key: null,
      suggested_question_key: "personal.first_name",
      confidence: 0.95,
      match_reason: "High lexical and semantic similarity to First Name / Vorname",
      alternatives: [],
    },
    {
      field_id: "f-geburtsdatum",
      field_key: "geburtsdatum",
      field_label: "Geburtsdatum",
      current_question_key: null,
      suggested_question_key: "person.date_of_birth",
      confidence: 0.94,
      match_reason: "Matched Date of Birth / Geburtsdatum",
      alternatives: [],
    },
  ],
};

const mockPublicOrgDetail: PublicOrganizationDetail = {
  id: "org-stuttgart",
  name: "Stadtverwaltung Stuttgart — Bürgeramt",
  slug: "stuttgart",
  organization_type: "government",
  verification_status: "verified_official",
  is_verified_government: true,
  description: "Official municipal registration office of Stuttgart.",
  office_address: "Eberhardstraße 37, 70173 Stuttgart",
  official_website_url: "https://www.stuttgart.de",
  contact_email: "buergeramt@stuttgart.de",
  has_logo: false,
  published_forms_count: 1,
  supported_languages: ["de", "en", "ar"],
  categories: [
    {
      id: "cat-wohnen",
      name: "Wohnen & Meldewesen",
      slug: "wohnen",
      icon: "home",
      forms_count: 1,
      sort_order: 1,
      translations: {
        en: { name: "Housing & Registration" },
        de: { name: "Wohnen & Meldewesen" },
      },
    },
  ],
  published_forms: [
    {
      id: "tmpl-1",
      key: "wohnungsgeberbestaetigung",
      name: "Wohnungsgeberbestätigung",
      description: "Bestätigung des Vermieters über den Einzug nach § 19 Bundesmeldegesetz",
      category: "wohnen",
      category_id: "cat-wohnen",
      category_slug: "wohnen",
      category_name: "Housing & Registration",
      submission_method: "print_and_sign",
      instructions: "Must be signed by the landlord upon moving in.",
      required_documents: ["Rental Contract", "ID Card"],
      active_version_id: "ver-1",
      version_number: 1,
      source_language: "de",
      supported_output_languages: ["de"],
      fields_count: 8,
      has_pdf: true,
    },
  ],
};

const mockSemanticSearchResults: FormSemanticSearchResult[] = [
  {
    template_id: "tmpl-1",
    key: "wohnungsgeberbestaetigung",
    title: "Wohnungsgeberbestätigung",
    description: "Bestätigung des Vermieters über den Einzug nach § 19 Bundesmeldegesetz",
    category_slug: "wohnen",
    category_name: "Housing & Registration",
    relevance_score: 0.92,
    match_type: "semantic",
    matched_reason: "High semantic match for landlord moving certificate",
  },
];

describe("Phase G5-AI: Semantic Auto-Mapper & Form Search", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("runs auto-map in FormSchemaReviewStudio and applies canonical mappings", async () => {
    vi.spyOn(portalClient, "getFormReview").mockResolvedValue(mockReview);
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listOrganizationCategories").mockResolvedValue([]);
    const autoMapSpy = vi
      .spyOn(portalClient, "autoMapFormFields")
      .mockResolvedValue(mockAutoMapResponse);
    const applySpy = vi
      .spyOn(portalClient, "applyAutoMapFormFields")
      .mockResolvedValue({ success: true, updated_fields_count: 2 });

    render(
      <FormSchemaReviewStudio
        templateId="tmpl-1"
        onBack={vi.fn()}
        canEdit={true}
      />
    );

    // Wait for review data to load
    await waitFor(() => {
      expect(screen.getByText("Anmeldung einer Wohnung")).toBeInTheDocument();
    });

    // Verify "Auto-Map Schema" button is visible
    const autoMapButton = screen.getByRole("button", { name: /auto-map schema/i });
    expect(autoMapButton).toBeInTheDocument();

    // Trigger auto-map
    fireEvent.click(autoMapButton);

    await waitFor(() => {
      expect(autoMapSpy).toHaveBeenCalledWith("tmpl-1");
    });

    // Check banner appears
    await waitFor(() => {
      expect(
        screen.getByText(/AI Auto-Mapping Ready: 2 of 2 fields matched/i)
      ).toBeInTheDocument();
    });

    // Verify suggestion badges appear on field cards
    expect(screen.getByText("personal.first_name")).toBeInTheDocument();
    expect(screen.getByText("person.date_of_birth")).toBeInTheDocument();

    // Click "Apply All"
    const applyAllBtn = screen.getByRole("button", { name: /apply all \(2\)/i });
    fireEvent.click(applyAllBtn);

    await waitFor(() => {
      expect(applySpy).toHaveBeenCalledWith("tmpl-1", [
        { field_id: "f-vorname", question_key: "personal.first_name" },
        { field_id: "f-geburtsdatum", question_key: "person.date_of_birth" },
      ]);
    });

    // Verify success confirmation
    await waitFor(() => {
      expect(
        screen.getByText(/Successfully applied 2 canonical Profile Vault mappings/i)
      ).toBeInTheDocument();
    });
  });

  it("performs multilingual semantic search on PublicOrganizationPortal and displays match badges", async () => {
    vi.spyOn(portalClient, "getPublicOrganizationBySlug").mockResolvedValue(mockPublicOrgDetail);
    const semanticSearchSpy = vi
      .spyOn(portalClient, "semanticSearchOrganizationForms")
      .mockResolvedValue(mockSemanticSearchResults);

    render(<PublicOrganizationPortal slug="stuttgart" />);

    // Wait for portal to load
    await waitFor(() => {
      expect(screen.getByText("Wohnungsgeberbestätigung")).toBeInTheDocument();
    });

    // Find search input
    const searchInput = screen.getByPlaceholderText(/search in your language/i);
    expect(searchInput).toBeInTheDocument();

    // Type a natural language query in English
    fireEvent.change(searchInput, { target: { value: "moving apartment landlord proof" } });

    // Wait for debounced semantic search to trigger
    await waitFor(
      () => {
        expect(semanticSearchSpy).toHaveBeenCalledWith(
          "stuttgart",
          "moving apartment landlord proof"
        );
      },
      { timeout: 1500 }
    );

    // Verify "Multilingual AI Semantic Search Active" badge is visible
    await waitFor(() => {
      expect(
        screen.getByText(/Multilingual AI Semantic Search Active/i)
      ).toBeInTheDocument();
    });

    // Verify form card displays Match 92% and match reason
    await waitFor(() => {
      expect(screen.getByText(/Match 92%/i)).toBeInTheDocument();
      expect(
        screen.getByText(/High semantic match for landlord moving certificate/i)
      ).toBeInTheDocument();
    });
  });
});
