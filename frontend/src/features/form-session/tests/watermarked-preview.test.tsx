import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ sessionId: "session-preview-1" }),
}));

const translateStub = (key: string) => key;

vi.mock("next-intl", () => ({
  useTranslations: () => translateStub,
}));

const getSummaryMock = vi.fn();
const fetchWatermarkedPreviewPdfBlobMock = vi.fn();

vi.mock("../services/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/apiClient")>();
  return {
    ...actual,
    getSummary: (...args: unknown[]) => getSummaryMock(...args),
    fetchWatermarkedPreviewPdfBlob: (...args: unknown[]) =>
      fetchWatermarkedPreviewPdfBlobMock(...args),
  };
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("SessionSummary — watermarked PDF preview (Phase S1-04)", () => {
  it("renders a watermarked PDF preview button and opens the preview blob on click", async () => {
    getSummaryMock.mockResolvedValue({
      sessionId: "session-preview-1",
      status: "in_progress",
      fields: [
        {
          fieldId: "f-1",
          fieldKey: "personal.first_name",
          label: "First Name",
          fieldType: "text",
          required: true,
          requiredness: "required",
          originalAnswer: "Олександр",
          normalizedValue: { value: "Олександр" },
          outputValue: "Олександр",
          status: "confirmed",
          answerState: "confirmed",
        },
      ],
    });
    fetchWatermarkedPreviewPdfBlobMock.mockResolvedValue(
      new Blob(["%PDF-1.7"], { type: "application/pdf" }),
    );

    const originalCreateObjectURL = URL.createObjectURL;
    const originalRevokeObjectURL = URL.revokeObjectURL;
    const createObjectUrlMock = vi.fn(() => "blob:http://localhost/preview-1");
    URL.createObjectURL = createObjectUrlMock;
    URL.revokeObjectURL = vi.fn();
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    const { default: SessionSummary } = await import(
      "@/app/application/session/[sessionId]/summary/page"
    );
    render(<SessionSummary />);

    const previewBtn = await screen.findByRole("button", {
      name: /previewPdf/i,
    });
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(fetchWatermarkedPreviewPdfBlobMock).toHaveBeenCalledWith(
        "session-preview-1",
      );
      expect(openSpy).toHaveBeenCalledWith(
        "blob:http://localhost/preview-1",
        "_blank",
        "noopener,noreferrer",
      );
    });

    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
    openSpy.mockRestore();
  });
});
