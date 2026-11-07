import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PortalDashboard } from "../components/PortalDashboard";
import { OrganizationCategoryManager } from "../components/OrganizationCategoryManager";
import * as portalClient from "../services/portalClient";
import { Organization, OrganizationCategory, OrganizationFormSummary } from "../types";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockOrg: Organization = {
  id: "org-1",
  name: "Stadtverwaltung Stuttgart",
  slug: "first-f95b49",
  billing_plan: "free",
  allowed_cases_per_month: 100,
  role: "owner",
  organization_type: "government",
  verification_status: "verified_official",
  is_verified_government: true,
  description: "Official municipal authority.",
  supported_languages: ["de", "en"],
  created_at: "2026-11-01T00:00:00Z",
};

const mockCategories: OrganizationCategory[] = [
  {
    id: "cat-housing",
    organization_id: "org-1",
    name: "Wohnen & Meldewesen",
    slug: "housing-residence",
    icon: "Home",
    sort_order: 10,
    is_active: true,
    forms_count: 1,
    translations: {
      en: { name: "Housing & Residence" },
      de: { name: "Wohnen & Meldewesen" },
    },
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
  },
  {
    id: "cat-family",
    organization_id: "org-1",
    name: "Familie & Kinder",
    slug: "family-children",
    icon: "Users",
    sort_order: 20,
    is_active: true,
    forms_count: 0,
    translations: {
      en: { name: "Family & Children" },
    },
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
  },
];

const mockForms: OrganizationFormSummary[] = [
  {
    id: "form-1",
    key: "wohnung-anmeldung",
    name: "Wohnungsgeberbestätigung",
    category: "Wohnen & Meldewesen",
    category_id: "cat-housing",
    category_name: "Wohnen & Meldewesen",
    category_slug: "housing-residence",
    category_icon: "Home",
    submissionMethod: "print_and_sign",
    requiredDocuments: [],
    versionNumber: 1,
    status: "published",
    fieldsCount: 5,
    hasPdf: true,
    createdAt: "2026-11-01T00:00:00Z",
    updatedAt: "2026-11-01T00:00:00Z",
  },
  {
    id: "form-2",
    key: "kindergeld-kg1",
    name: "Antrag auf Kindergeld",
    category: "general",
    category_id: null,
    category_name: null,
    submissionMethod: "print_and_sign",
    requiredDocuments: [],
    versionNumber: 1,
    status: "needs_review",
    fieldsCount: 8,
    hasPdf: true,
    createdAt: "2026-11-02T00:00:00Z",
    updatedAt: "2026-11-02T00:00:00Z",
  },
];

describe("Form Category Relations & Dashboard Management", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listOrganizationForms").mockResolvedValue(mockForms);
    vi.spyOn(portalClient, "listOrganizationCategories").mockResolvedValue(mockCategories);
    vi.spyOn(portalClient, "updateFormCategory").mockResolvedValue({
      ...mockForms[1],
      category_id: "cat-family",
      category_name: "Familie & Kinder",
      category_icon: "Users",
    });
    vi.spyOn(portalClient, "autoCategorizeForms").mockResolvedValue({
      categorized_count: 1,
      total_forms: 2,
      details: [{ form_id: "form-2", form_name: "Antrag auf Kindergeld", category: "Familie & Kinder" }],
    });
    vi.spyOn(portalClient, "getCategoryForms").mockResolvedValue(["form-1"]);
    vi.spyOn(portalClient, "assignCategoryForms").mockResolvedValue(["form-1", "form-2"]);
  });

  it("renders category filter pills on PortalDashboard and filters forms", async () => {
    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Wohnungsgeberbestätigung")).toBeInTheDocument();
      expect(screen.getByText("Antrag auf Kindergeld")).toBeInTheDocument();
    });

    // Check category pills exist
    expect(screen.getByText("All Categories")).toBeInTheDocument();
    expect(screen.getByText("Uncategorized")).toBeInTheDocument();

    // Filter by Uncategorized
    fireEvent.click(screen.getByText("Uncategorized"));

    // Only unassigned form remains visible
    expect(screen.queryByText("Wohnungsgeberbestätigung")).not.toBeInTheDocument();
    expect(screen.getByText("Antrag auf Kindergeld")).toBeInTheDocument();
  });

  it("allows quick categorization of an uncategorized form directly from the card", async () => {
    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Antrag auf Kindergeld")).toBeInTheDocument();
    });

    // Find the "+ Categorize" button on the uncategorized form card
    const categorizeBtn = screen.getByText("+ Categorize");
    fireEvent.click(categorizeBtn);

    // Dropdown popover should show available categories
    await waitFor(() => {
      expect(screen.getByText("Assign Category")).toBeInTheDocument();
    });

    // Click "Familie & Kinder" inside the Assign Category dropdown menu
    const assignCategoryHeader = screen.getByText("Assign Category");
    const dropdownMenu = assignCategoryHeader.parentElement!;
    const familyOption = dropdownMenu.querySelector("button")!;
    // Second button in categories list or click button containing "Familie & Kinder"
    const targetBtn = Array.from(dropdownMenu.querySelectorAll("button")).find((btn) =>
      btn.textContent?.includes("Familie & Kinder")
    );
    expect(targetBtn).toBeDefined();
    fireEvent.click(targetBtn!);

    await waitFor(() => {
      expect(portalClient.updateFormCategory).toHaveBeenCalledWith("form-2", "cat-family");
    });
  });

  it("triggers auto-categorization when clicking the Auto-Categorize button", async () => {
    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Auto-Categorize Official Forms")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Auto-Categorize Official Forms"));

    await waitFor(() => {
      expect(portalClient.autoCategorizeForms).toHaveBeenCalledTimes(1);
    });
  });

  it("manages assigned forms relation modal inside OrganizationCategoryManager", async () => {
    render(<OrganizationCategoryManager />);

    await waitFor(() => {
      expect(screen.getByText("Wohnen & Meldewesen")).toBeInTheDocument();
    });

    // Find the Manage Forms button on the first category card
    const manageBtns = screen.getAllByTitle(
      "Manage assigned official administrative forms"
    );
    expect(manageBtns.length).toBeGreaterThan(0);
    fireEvent.click(manageBtns[0]);

    // Modal opens
    await waitFor(() => {
      expect(screen.getByText(/Assign Forms to/)).toBeInTheDocument();
    });

    expect(portalClient.getCategoryForms).toHaveBeenCalledWith("cat-housing");

    // Click "Save Relations"
    const saveBtn = screen.getByText("Save Relations");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(portalClient.assignCategoryForms).toHaveBeenCalled();
    });
  });
});
