import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PublicOrganizationPortal } from "../components/PublicOrganizationPortal";
import { OrganizationCategoryManager } from "../components/OrganizationCategoryManager";
import * as portalClient from "../services/portalClient";
import { PublicOrganizationDetail, OrganizationCategory } from "../types";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  usePathname: () => "/organizations/first-f95b49",
}));

let mockCurrentLocale = "en";
const mockSetLocale = vi.fn((lang: string) => {
  mockCurrentLocale = lang;
});

vi.mock("@/features/form-session/components/LanguageProvider", () => ({
  useLanguage: () => ({
    locale: mockCurrentLocale,
    setLocale: mockSetLocale,
  }),
}));

const mockOrgWithCategories: PublicOrganizationDetail = {
  id: "org-stuttgart",
  name: "Stadtverwaltung Stuttgart — Bürgeramt & Ausländerwesen",
  slug: "first-f95b49",
  organization_type: "government",
  verification_status: "verified_official",
  is_verified_government: true,
  description: "Official municipal authority for citizen services.",
  office_address: "Eberhardstraße 39, 70173 Stuttgart",
  official_website_url: "https://www.stuttgart.de",
  contact_email: "buergerservice@stuttgart.de",
  has_logo: false,
  published_forms_count: 3,
  supported_languages: ["de", "en", "ar", "tr"],
  categories: [
    {
      id: "cat-housing",
      name: "Wohnen & Meldewesen",
      slug: "housing-residence",
      icon: "Home",
      sort_order: 10,
      forms_count: 2,
      translations: {
        en: { name: "Housing & Residence", description: "Apartment registration and moving." },
        de: { name: "Wohnen & Meldewesen", description: "Wohnungsanmeldung und Umzug." },
        ar: { name: "السكن وتسجيل الإقامة", description: "تسجيل السكن والإقامة." },
      },
    },
    {
      id: "cat-family",
      name: "Familie, Kinder & Partnerschaft",
      slug: "family-children",
      icon: "Users",
      sort_order: 20,
      forms_count: 1,
      translations: {
        en: { name: "Family & Children", description: "Birth, marriage, and childcare." },
        de: { name: "Familie, Kinder & Partnerschaft", description: "Geburt, Ehe und Kinder." },
        ar: { name: "الأسرة والأطفال", description: "المواليد والزواج ورعاية الأطفال." },
      },
    },
  ],
  published_forms: [
    {
      id: "tpl-anmeldung",
      key: "stuttgart-anmeldung",
      name: "Anmeldung einer Wohnung (§ 17 BMG)",
      description: "Official apartment registration for Stuttgart residents.",
      category: "housing-residence",
      category_id: "cat-housing",
      category_slug: "housing-residence",
      category_name: "Wohnen & Meldewesen",
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
    {
      id: "tpl-wohnungsgeber",
      key: "stuttgart-wohnungsgeber",
      name: "Wohnungsgeberbestätigung",
      description: "Landlord confirmation document according to § 19 BMG.",
      category: "housing-residence",
      category_id: "cat-housing",
      category_slug: "housing-residence",
      category_name: "Wohnen & Meldewesen",
      submission_method: "print_and_sign",
      instructions: "To be filled by landlord.",
      required_documents: ["Mietvertrag"],
      active_version_id: "ver-wohnungsgeber-1",
      version_number: 1,
      source_language: "de",
      supported_output_languages: ["de", "en"],
      fields_count: 8,
      has_pdf: true,
    },
    {
      id: "tpl-geburtsurkunde",
      key: "stuttgart-geburtsurkunde",
      name: "Antrag auf Ausstellung einer Geburtsurkunde",
      description: "Birth certificate request form.",
      category: "family-children",
      category_id: "cat-family",
      category_slug: "family-children",
      category_name: "Familie, Kinder & Partnerschaft",
      submission_method: "print_and_sign",
      instructions: "For persons born in Stuttgart.",
      required_documents: ["ID"],
      active_version_id: "ver-geburt-1",
      version_number: 1,
      source_language: "de",
      supported_output_languages: ["de", "en"],
      fields_count: 6,
      has_pdf: true,
    },
  ],
};

const mockCategoriesList: OrganizationCategory[] = [
  {
    id: "cat-housing",
    organization_id: "org-stuttgart",
    name: "Wohnen & Meldewesen",
    slug: "housing-residence",
    icon: "Home",
    sort_order: 10,
    is_active: true,
    forms_count: 2,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    translations: {
      en: { name: "Housing & Residence", description: "Apartment registration and moving." },
      de: { name: "Wohnen & Meldewesen", description: "Wohnungsanmeldung und Umzug." },
    },
  },
];

describe("TYPO3-Inspired Multilingual Form Categories & Public Portal Filtering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCurrentLocale = "en";
  });

  it("renders multilingual category filter pills on public organization portal in citizen language", async () => {
    vi.spyOn(portalClient, "getPublicOrganizationBySlug").mockResolvedValue(mockOrgWithCategories);

    render(<PublicOrganizationPortal slug="first-f95b49" />);

    // Wait for portal to load
    await waitFor(() => {
      expect(screen.getByText("Stadtverwaltung Stuttgart — Bürgeramt & Ausländerwesen")).toBeInTheDocument();
    });

    // In English locale, category titles should display their English translations
    expect(screen.getByText("Housing & Residence")).toBeInTheDocument();
    expect(screen.getByText("Family & Children")).toBeInTheDocument();

    // Verify all 3 forms are visible initially
    expect(screen.getByRole("heading", { name: "Anmeldung einer Wohnung (§ 17 BMG)" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Wohnungsgeberbestätigung" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Antrag auf Ausstellung einer Geburtsurkunde" })).toBeInTheDocument();
  });

  it("filters forms when a category pill is clicked and restores all forms when Show All is clicked", async () => {
    vi.spyOn(portalClient, "getPublicOrganizationBySlug").mockResolvedValue(mockOrgWithCategories);

    render(<PublicOrganizationPortal slug="first-f95b49" />);

    await waitFor(() => {
      expect(screen.getByText("Housing & Residence")).toBeInTheDocument();
    });

    // Click on Family & Children category pill
    const familyPill = screen.getByText("Family & Children");
    fireEvent.click(familyPill);

    // Only the birth certificate form should be visible
    expect(screen.getByRole("heading", { name: "Antrag auf Ausstellung einer Geburtsurkunde" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Anmeldung einer Wohnung (§ 17 BMG)" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Wohnungsgeberbestätigung" })).not.toBeInTheDocument();

    // Click Show All
    const showAllBtn = screen.getByText(/Show All/i);
    fireEvent.click(showAllBtn);

    // All forms should be restored
    expect(screen.getByRole("heading", { name: "Anmeldung einer Wohnung (§ 17 BMG)" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Wohnungsgeberbestätigung" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Antrag auf Ausstellung einer Geburtsurkunde" })).toBeInTheDocument();
  });

  it("translates category pills instantly when citizen changes guidance language", async () => {
    vi.spyOn(portalClient, "getPublicOrganizationBySlug").mockResolvedValue(mockOrgWithCategories);

    render(<PublicOrganizationPortal slug="first-f95b49" />);

    await waitFor(() => {
      expect(screen.getByText("Housing & Residence")).toBeInTheDocument();
    });

    // Citizen selects German language button
    const deBtn = screen.getByRole("button", { name: /Deutsch/i });
    fireEvent.click(deBtn);

    // Verify category label changed to German
    await waitFor(() => {
      expect(screen.getAllByText("Wohnen & Meldewesen").length).toBeGreaterThanOrEqual(1);
    });

    // Citizen selects Arabic language button
    const arBtn = screen.getByRole("button", { name: /العربية/i });
    fireEvent.click(arBtn);

    // Verify category label changed to Arabic
    await waitFor(() => {
      expect(screen.getByText("السكن وتسجيل الإقامة")).toBeInTheDocument();
      expect(screen.getByText("الأسرة والأطفال")).toBeInTheDocument();
    });
  });

  it("renders OrganizationCategoryManager and loads categories", async () => {
    vi.spyOn(portalClient, "listOrganizationCategories").mockResolvedValue(mockCategoriesList);

    render(<OrganizationCategoryManager />);

    await waitFor(() => {
      expect(screen.getByText("Form Categories")).toBeInTheDocument();
    });

    expect(screen.getByText("Wohnen & Meldewesen")).toBeInTheDocument();
    expect(screen.getByText(/2 Forms/i)).toBeInTheDocument();
  });
});
