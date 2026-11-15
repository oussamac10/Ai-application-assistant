import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { OrganizationCategoryManager } from "../components/OrganizationCategoryManager";
import * as portalClient from "../services/portalClient";
import { OrganizationCategory, Organization } from "../types";

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

const mockCategories: OrganizationCategory[] = [
  {
    id: "cat-1",
    organization_id: "org-1",
    name: "Wohnen & Meldewesen",
    slug: "wohnen-meldewesen",
    icon: "Home",
    description: "Anmeldung und Ummeldung",
    parent_id: null,
    sort_order: 10,
    is_active: true,
    translations: {
      en: { name: "Housing & Residence", description: "Registration and moving" },
    },
    forms_count: 2,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

describe("Category Translation Selection Flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listOrganizationCategories").mockResolvedValue(mockCategories);
    vi.spyOn(portalClient, "createOrganizationCategory").mockResolvedValue({
      id: "cat-2",
      organization_id: "org-1",
      name: "Familie & Kinder",
      slug: "familie-kinder",
      icon: "Users",
      description: null,
      parent_id: null,
      sort_order: 20,
      is_active: true,
      translations: {
        ar: { name: "الأسرة والأطفال", description: "خدمات الأسرة" },
      },
      forms_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  });

  it("relies on supported languages and allows user to pick a language from dropdown to translate", async () => {
    render(<OrganizationCategoryManager supportedLanguages={["de", "en", "ar", "fr"]} />);

    await waitFor(() => {
      expect(screen.getByText("Wohnen & Meldewesen")).toBeInTheDocument();
    });

    // Language count on category card reflects supported languages (4)
    expect(screen.getByText("1 / 4 Languages")).toBeInTheDocument();

    // Click "New Category"
    fireEvent.click(screen.getByText("New Category"));

    // Modal opens
    await waitFor(() => {
      expect(screen.getByText("Create Official Category")).toBeInTheDocument();
    });

    // Verify it explains that translations are based on Supported Guidance Languages (4)
    expect(
      screen.getByText("Based on Supported Guidance Languages (4)")
    ).toBeInTheDocument();

    // Verify it doesn't show all language inputs/tabs at once
    expect(screen.getByText("No language selected")).toBeInTheDocument();

    // The select dropdown contains only the organization's supported languages
    const select = screen.getByLabelText("Choose Language to Translate");
    expect(select).toBeInTheDocument();

    // Select Arabic ("ar") from the supported languages
    fireEvent.change(select, { target: { value: "ar" } });

    // Now the active translation editor appears for Arabic
    await waitFor(() => {
      expect(screen.getByText(/Translated Category Name \(AR\)/)).toBeInTheDocument();
    });

    // Fill in Primary Name and Arabic Translation
    const primaryNameInput = screen.getByLabelText("Category Name *");
    fireEvent.change(primaryNameInput, { target: { value: "Familie & Kinder" } });

    const arNameInput = screen.getByLabelText("Translated Category Name (AR) *");
    fireEvent.change(arNameInput, { target: { value: "الأسرة والأطفال" } });

    const arDescInput = screen.getByLabelText("Translated Description (AR)");
    fireEvent.change(arDescInput, { target: { value: "خدمات الأسرة" } });

    // Verify the added translation chip is displayed
    expect(screen.getAllByText(/العربية/).length).toBeGreaterThan(0);

    // Submit form
    fireEvent.click(screen.getByRole("button", { name: "Create Category" }));

    // Verify createOrganizationCategory was called with the selected translation
    await waitFor(() => {
      expect(portalClient.createOrganizationCategory).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Familie & Kinder",
          translations: {
            ar: {
              name: "الأسرة والأطفال",
              description: "خدمات الأسرة",
            },
          },
        })
      );
    });
  });

  it("allows removing a translation from the configured translations", async () => {
    render(<OrganizationCategoryManager supportedLanguages={["de", "en", "ar"]} />);

    await waitFor(() => {
      expect(screen.getByText("Wohnen & Meldewesen")).toBeInTheDocument();
    });

    // Click Edit Category
    fireEvent.click(screen.getByTitle("Edit Category"));

    await waitFor(() => {
      expect(screen.getByText("Edit Category & Translations")).toBeInTheDocument();
    });

    // Existing English translation should be present
    expect(screen.getByDisplayValue("Housing & Residence")).toBeInTheDocument();

    // Click remove on the active editor
    const removeBtn = screen.getByTitle("Remove active translation");
    fireEvent.click(removeBtn);

    // It should now show "No language selected"
    await waitFor(() => {
      expect(screen.getByText("No language selected")).toBeInTheDocument();
    });
  });
});
