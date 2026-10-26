import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ sessionId: "session-studio-1" }),
}));

const translateStub = (key: string, params?: Record<string, unknown>) =>
  params && "count" in params ? `${key}:${params.count}` : key;

vi.mock("next-intl", () => ({
  useTranslations: () => translateStub,
}));

const authStateMock = vi.fn(() => ({
  user: {
    id: "user-1",
    email: "applicant@example.com",
    createdAt: "2026-10-26T00:00:00Z",
  },
  loading: false,
}));

vi.mock("@/features/auth/context/AuthProvider", () => ({
  useAuth: () => authStateMock(),
  useOptionalAuth: () => authStateMock(),
}));

const getSummaryMock = vi.fn();
const reopenFieldMock = vi.fn();
const fetchWatermarkedPreviewPdfBlobMock = vi.fn();
const startSessionMock = vi.fn();
const getCurrentFieldMock = vi.fn();
const confirmAnswerMock = vi.fn();

vi.mock("../services/apiClient", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/apiClient")>();
  return {
    ...actual,
    getSummary: (...args: unknown[]) => getSummaryMock(...args),
    reopenField: (...args: unknown[]) => reopenFieldMock(...args),
    fetchWatermarkedPreviewPdfBlob: (...args: unknown[]) =>
      fetchWatermarkedPreviewPdfBlobMock(...args),
    startSession: (...args: unknown[]) => startSessionMock(...args),
    getCurrentField: (...args: unknown[]) => getCurrentFieldMock(...args),
    confirmAnswer: (...args: unknown[]) => confirmAnswerMock(...args),
  };
});

const saveSessionToVaultMock = vi.fn();
const prefillSessionFromVaultMock = vi.fn();

vi.mock("@/features/profile-vault/services/vaultClient", () => ({
  saveSessionToVault: (...args: unknown[]) => saveSessionToVaultMock(...args),
  prefillSessionFromVault: (...args: unknown[]) =>
    prefillSessionFromVaultMock(...args),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("Phase S2 — Verification Studio & Profile Vault Pre-Fill", () => {
  it("renders sourceLabel alongside translated label and cross-field consistency warnings", async () => {
    getSummaryMock.mockResolvedValue({
      fields: [
        {
          fieldId: "f-dob",
          fieldKey: "person.date_of_birth",
          fieldType: "date",
          label: "Date of Birth",
          sourceLabel: "Geburtsdatum",
          required: true,
          requiredness: "required",
          originalAnswer: "2099-01-01",
          normalizedValue: "2099-01-01",
          outputValue: "01.01.2099",
          status: "confirmed",
          answerState: "answered",
        },
      ],
      consistencyWarnings: [
        {
          code: "birth_date_in_future",
          severity: "warning",
          fieldKeys: ["person.date_of_birth"],
          message: "The date of birth is in the future.",
        },
      ],
      sourceLanguage: "de",
      userLanguage: "en",
      outputLanguage: "de",
      exportSupported: true,
    });
    reopenFieldMock.mockResolvedValue({ fieldId: "f-dob", position: 1 });

    const { default: SessionSummary } = await import(
      "@/app/application/session/[sessionId]/summary/page"
    );
    render(<SessionSummary />);

    expect(await screen.findByText("Date of Birth")).toBeTruthy();
    expect(screen.getByText("Geburtsdatum")).toBeTruthy();

    const warningPanel = screen.getByTestId("consistency-warnings-panel");
    expect(warningPanel.textContent).toContain(
      "The date of birth is in the future.",
    );

    const fixBtn = screen.getByTestId(
      "warning-edit-person.date_of_birth",
    );
    fireEvent.click(fixBtn);

    await waitFor(() => {
      expect(reopenFieldMock).toHaveBeenCalledWith("session-studio-1", "f-dob");
    });
  });

  it("toggles embedded side-by-side watermarked PDF preview in SessionSummary", async () => {
    getSummaryMock.mockResolvedValue({
      fields: [
        {
          fieldId: "f-1",
          fieldKey: "personal.first_name",
          fieldType: "text",
          label: "First Name",
          sourceLabel: "Vorname",
          required: true,
          requiredness: "required",
          originalAnswer: "Amira",
          normalizedValue: "Amira",
          outputValue: "Amira",
          status: "confirmed",
          answerState: "answered",
        },
      ],
      consistencyWarnings: [],
      exportSupported: true,
    });
    fetchWatermarkedPreviewPdfBlobMock.mockResolvedValue(
      new Blob(["%PDF-1.7"], { type: "application/pdf" }),
    );

    const originalCreateObjectURL = URL.createObjectURL;
    const originalRevokeObjectURL = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn(() => "blob:http://localhost/inline-preview");
    URL.revokeObjectURL = vi.fn();

    const { default: SessionSummary } = await import(
      "@/app/application/session/[sessionId]/summary/page"
    );
    render(<SessionSummary />);

    const toggleBtn = await screen.findByTestId("toggle-inline-preview");
    fireEvent.click(toggleBtn);

    await waitFor(() => {
      expect(fetchWatermarkedPreviewPdfBlobMock).toHaveBeenCalledWith(
        "session-studio-1",
      );
      const frame = screen.getByTestId(
        "inline-pdf-preview-frame",
      ) as HTMLIFrameElement;
      expect(frame.getAttribute("src")).toBe(
        "blob:http://localhost/inline-preview",
      );
    });

    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
  });

  it("saves confirmed answers to Profile Vault from SessionSummary when authenticated", async () => {
    getSummaryMock.mockResolvedValue({
      fields: [
        {
          fieldId: "f-1",
          fieldKey: "personal.first_name",
          fieldType: "text",
          label: "First Name",
          required: true,
          requiredness: "required",
          originalAnswer: "Amira",
          normalizedValue: "Amira",
          outputValue: "Amira",
          status: "confirmed",
          answerState: "answered",
        },
      ],
      consistencyWarnings: [],
    });
    saveSessionToVaultMock.mockResolvedValue({
      savedCount: 1,
      savedKeys: ["personal.first_name"],
    });

    const { default: SessionSummary } = await import(
      "@/app/application/session/[sessionId]/summary/page"
    );
    render(<SessionSummary />);

    const saveBtn = await screen.findByTestId("save-to-vault-btn");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(saveSessionToVaultMock).toHaveBeenCalledWith("session-studio-1");
    });
  });

  it("pre-fills unanswered questions from Profile Vault in GuidedSession and confirms in 1 click", async () => {
    startSessionMock.mockResolvedValue({
      publicId: "session-studio-1",
      status: "in_progress",
      userLanguage: "en",
      outputLanguage: "de",
      expiresAt: "2026-10-27T00:00:00Z",
    });
    getCurrentFieldMock
      .mockResolvedValueOnce({
        id: "f-1",
        fieldId: "f-1",
        key: "personal.first_name",
        fieldKey: "personal.first_name",
        fieldType: "text",
        required: true,
        requiredness: "required",
        position: 1,
        label: "First Name",
        currentAnswerId: null,
        currentAnswerStatus: null,
        originalAnswer: null,
        normalizedValue: null,
        outputValue: null,
        progress: {
          confirmedRequiredFields: 0,
          totalRequiredFields: 2,
          totalQuestions: 2,
          answeredQuestions: 0,
          percentage: 0,
        },
      })
      .mockResolvedValueOnce({
        id: "f-1",
        fieldId: "f-1",
        key: "personal.first_name",
        fieldKey: "personal.first_name",
        fieldType: "text",
        required: true,
        requiredness: "required",
        position: 1,
        label: "First Name",
        currentAnswerId: "ans-vault-1",
        currentAnswerStatus: "awaiting_confirmation",
        originalAnswer: "Amira",
        normalizedValue: "Amira",
        outputValue: "Amira",
        progress: {
          confirmedRequiredFields: 0,
          totalRequiredFields: 2,
          totalQuestions: 2,
          answeredQuestions: 0,
          percentage: 0,
        },
      })
      .mockResolvedValueOnce({
        id: "f-2",
        fieldId: "f-2",
        key: "personal.last_name",
        fieldKey: "personal.last_name",
        fieldType: "text",
        required: true,
        requiredness: "required",
        position: 2,
        label: "Last Name",
        currentAnswerId: null,
        currentAnswerStatus: null,
        originalAnswer: null,
        normalizedValue: null,
        outputValue: null,
        progress: {
          confirmedRequiredFields: 1,
          totalRequiredFields: 2,
          totalQuestions: 2,
          answeredQuestions: 1,
          percentage: 50,
        },
      });
    prefillSessionFromVaultMock.mockResolvedValue({
      prefilledCount: 1,
      prefilledFieldKeys: ["personal.first_name"],
    });
    confirmAnswerMock.mockResolvedValue({
      id: "ans-vault-1",
      originalAnswer: "Amira",
      outputValue: "Amira",
      status: "confirmed",
    });

    const { default: GuidedSession } = await import(
      "@/app/application/session/[sessionId]/page"
    );
    render(<GuidedSession />);

    const prefillBtn = await screen.findByTestId("prefill-from-vault-btn");
    fireEvent.click(prefillBtn);

    await waitFor(() => {
      expect(prefillSessionFromVaultMock).toHaveBeenCalledWith(
        "session-studio-1",
      );
    });

    const confirmPrefilledBtn = await screen.findByTestId(
      "confirm-prefilled-btn",
    );
    fireEvent.click(confirmPrefilledBtn);

    await waitFor(() => {
      expect(confirmAnswerMock).toHaveBeenCalledWith(
        "session-studio-1",
        "ans-vault-1",
      );
    });
  });
});
