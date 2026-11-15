import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FormSchemaReviewStudio } from "../components/FormSchemaReviewStudio";
import * as portalClient from "../services/portalClient";
import type { FormReviewDetail, Organization } from "../types";

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
  supported_languages: ["de", "en", "ar"],
  created_at: new Date().toISOString(),
};

const baseReview: FormReviewDetail = {
  templateId: "tmpl-1",
  versionId: "ver-1",
  key: "wbs-stuttgart",
  name: "Wohnberechtigungsschein",
  category: "wohnen",
  submissionMethod: "print_and_sign",
  status: "needs_review",
  versionNumber: 1,
  sourceLanguage: "de",
  pageCount: 1,
  requiredDocuments: [],
  fields: [
    {
      id: "t-r1-name",
      key: "hh_1_name",
      fieldType: "string",
      required: true,
      requiredness: "required",
      position: 0,
      configuration: {
        page: 1,
        bbox: [40, 200, 180, 220],
        learned_pattern_id: "pat-1",
        table: {
          table_key: "hh",
          table_title: "Household members",
          row_index: 1,
          total_rows: 2,
          row_label: "Applicant",
          row_role: "applicant",
          col_index: 0,
          column_header: "Name",
        },
      },
      translations: [{ language: "de", label: "Name" }],
      options: [],
    },
    {
      id: "t-r1-sex",
      key: "hh_1_sex",
      fieldType: "single_choice",
      required: false,
      requiredness: "optional",
      position: 1,
      configuration: {
        page: 1,
        bbox: [200, 200, 320, 220],
        option_boxes: [
          { value: "m", label: "m", page: 1, bbox: [200, 202, 212, 214] },
          { value: "w", label: "w", page: 1, bbox: [235, 202, 247, 214] },
          { value: "d", label: "d", page: 1, bbox: [270, 202, 282, 214] },
        ],
        table: {
          table_key: "hh",
          table_title: "Household members",
          row_index: 1,
          total_rows: 2,
          row_label: "Applicant",
          row_role: "applicant",
          col_index: 1,
          column_header: "Gender",
        },
      },
      translations: [{ language: "de", label: "Geschlecht" }],
      options: [
        { value: "m", label: "m", position: 1, translations: [{ language: "de", label: "m" }] },
        { value: "w", label: "w", position: 2, translations: [{ language: "de", label: "w" }] },
        { value: "d", label: "d", position: 3, translations: [{ language: "de", label: "d" }] },
      ],
    },
    {
      id: "t-r2-name",
      key: "hh_2_name",
      fieldType: "string",
      required: false,
      requiredness: "optional",
      position: 2,
      configuration: {
        page: 1,
        bbox: [40, 230, 180, 250],
        table: {
          table_key: "hh",
          table_title: "Household members",
          row_index: 2,
          total_rows: 2,
          row_label: "Member 2",
          row_role: "member",
          col_index: 0,
          column_header: "Name",
        },
      },
      translations: [{ language: "de", label: "Name" }],
      options: [],
    },
    {
      id: "chk-ft",
      key: "chk_fulltime",
      fieldType: "boolean",
      required: false,
      requiredness: "optional",
      position: 3,
      configuration: { page: 1, bbox: [50, 320, 64, 334] },
      translations: [{ language: "de", label: "Vollzeit" }],
      options: [],
    },
    {
      id: "chk-pt",
      key: "chk_parttime",
      fieldType: "boolean",
      required: false,
      requiredness: "optional",
      position: 4,
      configuration: { page: 1, bbox: [50, 350, 64, 364] },
      translations: [{ language: "de", label: "Teilzeit" }],
      options: [],
    },
  ],
};

describe("FormSchemaReviewStudio Table Groups, Choice Editing & Selection Actions", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(portalClient, "getFormReview").mockResolvedValue(baseReview);
    vi.spyOn(portalClient, "getCurrentOrganization").mockResolvedValue(mockOrg);
    vi.spyOn(portalClient, "listOrganizationCategories").mockResolvedValue([]);
  });

  it("renders table group row tabs, badges, inline choice options, and syncs Row 1 settings", async () => {
    const syncSpy = vi
      .spyOn(portalClient, "syncTableColumns")
      .mockResolvedValue(baseReview);

    render(<FormSchemaReviewStudio templateId="tmpl-1" onBack={vi.fn()} />);

    expect(await screen.findByTestId("review-table-group-hh")).toBeInTheDocument();
    expect(screen.getByText("2 rows · 2 columns")).toBeInTheDocument();
    expect(screen.getByText("Recognized from past forms")).toBeInTheDocument();
    expect(screen.getByText("Linked to 3 PDF checkboxes")).toBeInTheDocument();
    expect(screen.getByText("Answer Choices (3)")).toBeInTheDocument();

    // Switch active row tab to Row 2
    fireEvent.click(screen.getByRole("tab", { name: /Row 2 · Member 2/i }));
    expect(screen.queryByText("Linked to 3 PDF checkboxes")).not.toBeInTheDocument();

    // Apply Row 1 settings to all rows
    fireEvent.click(
      screen.getByRole("button", { name: /Apply Row 1 settings to all rows/i })
    );
    await waitFor(() => {
      expect(syncSpy).toHaveBeenCalledWith("tmpl-1", "hh", 1);
    });
  });

  it("combines multiple selected boolean fields into one choice question", async () => {
    const combineSpy = vi
      .spyOn(portalClient, "combineFieldsIntoChoice")
      .mockResolvedValue(baseReview);

    render(<FormSchemaReviewStudio templateId="tmpl-1" onBack={vi.fn()} />);
    await screen.findByText("Wohnberechtigungsschein");

    fireEvent.click(screen.getByLabelText("Select Vollzeit"));
    fireEvent.click(screen.getByLabelText("Select Teilzeit"));

    const bar = await screen.findByTestId("studio-selection-bar");
    expect(bar).toHaveTextContent("2 fields selected");

    fireEvent.click(
      screen.getByRole("button", { name: /Combine into Choice Question/i })
    );

    const labelInput = screen.getByPlaceholderText(
      "e.g. Marital status or Gender"
    );
    fireEvent.change(labelInput, { target: { value: "Employment type" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm Combine" }));

    await waitFor(() => {
      expect(combineSpy).toHaveBeenCalledWith("tmpl-1", {
        fieldIds: ["chk-ft", "chk-pt"],
        label: "Employment type",
        fieldType: "single_choice",
      });
    });
  });
});
