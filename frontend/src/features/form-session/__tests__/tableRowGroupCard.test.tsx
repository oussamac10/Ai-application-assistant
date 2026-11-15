import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import enMessages from "../../../../messages/en.json";
import { TableRowGroupCard } from "../components/TableRowGroupCard";
import type { TableRowContext } from "../services/apiClient";

vi.mock("next-intl", () => ({
  useTranslations: (ns: string) => (key: string, params?: Record<string, unknown>) => {
    const bucket = (enMessages as Record<string, Record<string, string>>)[ns] || {};
    let template = bucket[key] ?? key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        template = template.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
      }
    }
    return template;
  },
}));

const submitTableRowMock = vi.fn();
const skipTableRowMock = vi.fn();

vi.mock("../services/apiClient", () => ({
  submitTableRow: (...args: unknown[]) => submitTableRowMock(...args),
  skipTableRow: (...args: unknown[]) => skipTableRowMock(...args),
}));

const ROW_1_CONTEXT: TableRowContext = {
  tableKey: "hh",
  tableTitle: "Household members",
  tableDescription: "List every person living in the apartment.",
  rowIndex: 1,
  totalRows: 3,
  rowLabel: "Applicant",
  fields: [
    {
      fieldId: "f-r1-dob",
      fieldKey: "hh_1_dob",
      fieldType: "date",
      label: "Date of birth",
      required: true,
      requiredness: "required",
      options: [],
    },
    {
      fieldId: "f-r1-nat",
      fieldKey: "hh_1_nat",
      fieldType: "country",
      label: "Nationality",
      required: true,
      requiredness: "required",
      options: [],
    },
    {
      fieldId: "f-r1-inc",
      fieldKey: "hh_1_income",
      fieldType: "choice",
      label: "Own income",
      required: false,
      requiredness: "optional",
      options: [
        { value: "ja", label: "Yes" },
        { value: "nein", label: "No" },
      ],
    },
  ],
  rowsOverview: [
    {
      rowIndex: 1,
      rowLabel: "Applicant",
      status: "unanswered",
      firstFieldId: "f-r1-dob",
      firstFieldKey: "hh_1_dob",
      answeredCount: 0,
      totalCount: 3,
    },
    {
      rowIndex: 2,
      rowLabel: "Member 2",
      status: "unanswered",
      firstFieldId: "f-r2-dob",
      firstFieldKey: "hh_2_dob",
      answeredCount: 0,
      totalCount: 3,
    },
  ],
};

describe("TableRowGroupCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders rowsOverview tabs, compact 1-tap choice pills, and maps validation errors to friendly messages", async () => {
    submitTableRowMock.mockResolvedValueOnce({
      status: "validation_error",
      submittedCount: 0,
      skippedCount: 0,
      fieldErrors: [
        {
          fieldId: "f-r1-nat",
          fieldKey: "hh_1_nat",
          label: "Nationality",
          reasonCode: "invalid_country",
        },
      ],
      clarificationFieldIds: [],
    });

    const onSelectRow = vi.fn().mockResolvedValue(undefined);
    const onRowCompleted = vi.fn().mockResolvedValue(undefined);

    render(
      <TableRowGroupCard
        sessionId="sess-1"
        tableRow={ROW_1_CONTEXT}
        onRowCompleted={onRowCompleted}
        onSelectRow={onSelectRow}
        onSwitchToSingleField={vi.fn()}
      />
    );

    expect(screen.getByText("Row 1 of 3")).toBeInTheDocument();
    const member2Tab = screen.getByRole("tab", { name: /Member 2/i });
    fireEvent.click(member2Tab);
    expect(onSelectRow).toHaveBeenCalledWith("f-r2-dob");

    // 1-tap compact choice pill rendered instead of raw dropdown
    const yesPill = screen.getByRole("radio", { name: "Yes" });
    fireEvent.click(yesPill);
    expect(yesPill).toHaveAttribute("aria-checked", "true");

    // Fill date and invalid country then submit
    fireEvent.change(screen.getByLabelText(/Date of birth/i), {
      target: { value: "1990-04-15" },
    });
    fireEvent.change(screen.getByLabelText(/Nationality/i), {
      target: { value: "Neverland" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Save Row & Continue/i }));

    await waitFor(() => {
      expect(submitTableRowMock).toHaveBeenCalledWith("sess-1", [
        { fieldId: "f-r1-dob", value: "1990-04-15" },
        { fieldId: "f-r1-nat", value: "Neverland" },
        { fieldId: "f-r1-inc", value: "ja" },
      ]);
    });

    expect(
      screen.getByText(
        "Please enter a valid country or nationality (for example, Germany or DE)."
      )
    ).toBeInTheDocument();
    expect(screen.queryByText(/^validation$/i)).not.toBeInTheDocument();
    expect(onRowCompleted).not.toHaveBeenCalled();
  });

  it("supports skipping all remaining empty rows on optional member rows", async () => {
    skipTableRowMock.mockResolvedValueOnce({
      status: "ok",
      submittedCount: 0,
      skippedCount: 6,
      fieldErrors: [],
      clarificationFieldIds: [],
    });

    const onRowCompleted = vi.fn().mockResolvedValue(undefined);
    const optionalRow2: TableRowContext = {
      ...ROW_1_CONTEXT,
      rowIndex: 2,
      rowLabel: "Member 2",
      fields: ROW_1_CONTEXT.fields.map((f) => ({
        ...f,
        fieldId: f.fieldId.replace("r1", "r2"),
        fieldKey: f.fieldKey.replace("_1_", "_2_"),
        required: false,
        requiredness: "optional",
      })),
    };

    render(
      <TableRowGroupCard
        sessionId="sess-1"
        tableRow={optionalRow2}
        onRowCompleted={onRowCompleted}
        onSwitchToSingleField={vi.fn()}
      />
    );

    const skipAllBtn = screen.getByRole("button", {
      name: /Skip remaining empty rows/i,
    });
    fireEvent.click(skipAllBtn);

    await waitFor(() => {
      expect(skipTableRowMock).toHaveBeenCalledWith("sess-1", {
        fieldIds: ["f-r2-dob", "f-r2-nat", "f-r2-inc"],
        skipRemainingEmptyRows: true,
        tableKey: "hh",
        fromRowIndex: 2,
      });
    });
    expect(onRowCompleted).toHaveBeenCalled();
  });
});
