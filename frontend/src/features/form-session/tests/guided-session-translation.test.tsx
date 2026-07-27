import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ sessionId: "session-1" }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/features/form-session/services/sessionCredentials", () => ({
  getSessionToken: () => "test-token",
  removeSessionToken: vi.fn(),
}));

const startSessionMock = vi.fn();
const getCurrentFieldMock = vi.fn();
const submitAnswerMock = vi.fn();
const confirmAnswerMock = vi.fn();
const getSummaryMock = vi.fn();

vi.mock("@/features/form-session/services/apiClient", () => ({
  startSession: (...args: unknown[]) => startSessionMock(...args),
  getCurrentField: (...args: unknown[]) => getCurrentFieldMock(...args),
  submitAnswer: (...args: unknown[]) => submitAnswerMock(...args),
  submitClarification: vi.fn(),
  confirmAnswer: (...args: unknown[]) => confirmAnswerMock(...args),
  previousField: vi.fn(),
  changeAnswer: vi.fn(),
  getSummary: (...args: unknown[]) => getSummaryMock(...args),
}));

// Mirrors what the fixed backend returns for a German-language session:
// display labels are translated, but the stable option `value`s (used by
// answer validation) remain the original English source strings.
const GERMAN_CATEGORY_FIELD = {
  fieldId: "field-category",
  fieldKey: "request_category",
  id: "field-category",
  key: "request_category",
  fieldType: "multiple_choice",
  required: true,
  position: 1,
  label: "Wie lautet Ihr vollständiger Name?",
  helpText: null,
  placeholder: null,
  options: [
    { value: "Housing", label: "Wohnen" },
    { value: "Education", label: "Bildung" },
    { value: "Medical", label: "Medizinisch" },
  ],
  currentAnswerStatus: null,
  progress: { confirmedRequiredFields: 0, totalRequiredFields: 1, percentage: 0 },
};

describe("Guided session — translated question and choice display", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    startSessionMock.mockResolvedValue({ status: "in_progress" });
    getCurrentFieldMock.mockResolvedValue(GERMAN_CATEGORY_FIELD);
    getSummaryMock.mockRejectedValue(new Error("no summary yet"));
  });

  afterEach(() => {
    vi.resetModules();
  });

  it("displays the German-translated question label and choice labels", async () => {
    const { default: GuidedSession } = await import(
      "@/app/application/session/[sessionId]/page"
    );
    render(<GuidedSession />);

    await waitFor(() =>
      expect(screen.getByText("Wie lautet Ihr vollständiger Name?")).toBeDefined()
    );

    expect(screen.getByLabelText("Wohnen")).toBeDefined();
    expect(screen.getByLabelText("Bildung")).toBeDefined();
    expect(screen.getByLabelText("Medizinisch")).toBeDefined();

    // The untranslated English label text must not appear anywhere.
    expect(screen.queryByText("Request category")).toBeNull();
    expect(screen.queryByLabelText("Housing")).toBeNull();
  });

  it("submits the stable English option values, not the displayed German labels", async () => {
    submitAnswerMock.mockResolvedValue({
      id: "answer-1",
      status: "awaiting_confirmation",
      requiresClarification: false,
      validationStatus: "valid",
      originalAnswer: '["Housing","Education"]',
      normalizedValue: ["Housing", "Education"],
      outputValue: "Housing, Education",
    });

    const { default: GuidedSession } = await import(
      "@/app/application/session/[sessionId]/page"
    );
    render(<GuidedSession />);

    await waitFor(() => expect(screen.getByLabelText("Wohnen")).toBeDefined());

    fireEvent.click(screen.getByLabelText("Wohnen"));
    fireEvent.click(screen.getByLabelText("Bildung"));
    fireEvent.click(screen.getByText("continue"));

    await waitFor(() =>
      expect(submitAnswerMock).toHaveBeenCalledWith(
        "session-1",
        "field-category",
        JSON.stringify(["Housing", "Education"])
      )
    );
  });
});
