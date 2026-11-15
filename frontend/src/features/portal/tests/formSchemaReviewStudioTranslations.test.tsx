import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FormSchemaReviewStudio } from "../components/FormSchemaReviewStudio";
import * as portalClient from "../services/portalClient";
import { FormReviewDetail, Organization } from "../types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
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
  key: "wohnungsgeberbestaetigung",
  name: "Wohnungsgeberbestätigung",
  category: "wohnen",
  submissionMethod: "print_and_sign",
  status: "needs_review",
  versionNumber: 1,
  sourceLanguage: "de",
  pageCount: 1,
  requiredDocuments: [],
  fields: [
    {
      id: "f-1",
      key: "chk_einzug",
      fieldType: "boolean",
      required: true,
      requiredness: "required",
      position: 0,
      configuration: { page: 1, bbox: [50, 100, 70, 120] },
      translations: [
        {
          language: "de",
          label: "Einzugsbestätigung des Wohnungsgebers nach § 19 BMG",
        },
      ],
      options: [],
    },
  ],
};

describe("FormSchemaReviewStudio Translations & ModernSelect", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(portalClient, "getFormReview").mockResolvedValue(mockReview);
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listOrganizationCategories").mockResolvedValue([]);
    vi.spyOn(portalClient, "translateFormFieldLabel").mockResolvedValue({
      ar: "تأكيد الانتقال للسكن من المؤجر وفقاً للمادة 19",
      en: "Confirmation of moving in by the landlord according to Section 19 BMG",
      fr: "Confirmation d'emménagement par le bailleur selon l'article 19",
    });
    vi.spyOn(portalClient, "updateFormField").mockResolvedValue({
      ...mockReview.fields[0],
      translations: [
        {
          language: "de",
          label: "Einzugsbestätigung des Wohnungsgebers nach § 19 BMG",
        },
        {
          language: "ar",
          label: "تأكيد الانتقال للسكن من المؤجر وفقاً للمادة 19",
        },
      ],
    });
    vi.spyOn(portalClient, "updateFormReview").mockResolvedValue(mockReview);
    vi.spyOn(portalClient, "reorderFormFields").mockResolvedValue([]);
  });

  it("renders authentic detected German field label and ModernSelect controls", async () => {
    render(
      <FormSchemaReviewStudio
        templateId="tmpl-1"
        onBack={vi.fn()}
        canEdit={true}
      />
    );

    // Should load the form title
    await waitFor(() => {
      expect(screen.getByText("Wohnungsgeberbestätigung")).toBeInTheDocument();
    });

    // Should display the authentic detected German label in the input
    const labelInput = screen.getByDisplayValue(
      "Einzugsbestätigung des Wohnungsgebers nach § 19 BMG"
    );
    expect(labelInput).toBeInTheDocument();

    // Should display ModernSelect for Input Type
    expect(screen.getAllByLabelText("Input Type").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("Requirement").length).toBeGreaterThan(0);
  });

  it("expands Citizen Guidance Translations and supports 1-click Auto-Translate", async () => {
    render(
      <FormSchemaReviewStudio
        templateId="tmpl-1"
        onBack={vi.fn()}
        canEdit={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Question Translations")).toBeInTheDocument();
    });

    // Expand translations drawer
    const expandBtn = screen.getByRole("button", {
      name: /Question Translations/i,
    });
    fireEvent.click(expandBtn);

    // Language tabs should be visible for supported languages (de, en, ar, fr)
    await waitFor(() => {
      expect(screen.getByText(/العربية/i)).toBeInTheDocument();
    });

    // Click Translate All
    const autoTranslateAllBtn = screen.getByRole("button", {
      name: /Translate All/i,
    });
    fireEvent.click(autoTranslateAllBtn);

    await waitFor(() => {
      expect(portalClient.translateFormFieldLabel).toHaveBeenCalledWith(
        "Einzugsbestätigung des Wohnungsgebers nach § 19 BMG",
        "de",
        expect.arrayContaining(["en", "ar", "fr"])
      );
    });
  });
});
