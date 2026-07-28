import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useParams: () => ({ sessionId: "session-1" }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/features/form-session/services/sessionCredentials", () => ({
  getSessionToken: () => "test-token",
  removeSessionToken: vi.fn(),
}));

vi.mock("@/features/auth/context/AuthProvider", () => ({
  useAuth: () => ({
    user: null,
    loading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  }),
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

const BIO_FIELD = {
  fieldId: "field-bio",
  fieldKey: "bio",
  id: "field-bio",
  key: "bio",
  fieldType: "multiline_text",
  required: false,
  position: 1,
  label: "Situation",
  helpText: null,
  placeholder: null,
  options: null,
  currentAnswerStatus: null,
  progress: { confirmedRequiredFields: 0, totalRequiredFields: 1, percentage: 0 },
};

async function submitBioAnswer(answer: string) {
  const { default: GuidedSession } = await import(
    "@/app/application/session/[sessionId]/page"
  );
  render(<GuidedSession />);

  await waitFor(() => expect(screen.getByText("Situation")).toBeDefined());

  const field = (document.querySelector("textarea") ||
    document.querySelector("input[type='text']")) as HTMLTextAreaElement | HTMLInputElement;
  fireEvent.change(field, { target: { value: answer } });
  fireEvent.click(screen.getByText("continue"));

  await waitFor(() => expect(submitAnswerMock).toHaveBeenCalled());
  await waitFor(() => expect(screen.getByText("confirmTitle")).toBeDefined());
}

describe("Guided session — proposed-value display (Ollama parsing bug regression)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    startSessionMock.mockResolvedValue({ status: "in_progress" });
    getCurrentFieldMock.mockResolvedValue(BIO_FIELD);
    getSummaryMock.mockRejectedValue(new Error("no summary yet"));
  });

  afterEach(() => {
    vi.resetModules();
  });

  it("renders the proposed value as a plain string for the exact reported example", async () => {
    submitAnswerMock.mockResolvedValue({
      id: "answer-1",
      status: "awaiting_confirmation",
      requiresClarification: false,
      validationStatus: "valid",
      originalAnswer: "Je suis marié",
      normalizedValue: "I am married",
      outputValue: "I am married",
    });

    await submitBioAnswer("Je suis marié");

    expect(screen.getByText("I am married")).toBeDefined();
  });

  it("never renders a raw object as the proposed value", async () => {
    submitAnswerMock.mockResolvedValue({
      id: "answer-1",
      status: "awaiting_confirmation",
      requiresClarification: false,
      validationStatus: "valid",
      originalAnswer: "Je suis marié",
      // Simulates a malformed shape slipping through (defense in depth —
      // the backend now rejects this before it reaches the client at all,
      // see backend/app/ai/ollama_provider.py's strict schema validation).
      normalizedValue: {
        [
          "The user's answer 'Je suis marié' translates to 'I am married' " +
            "in French, but the field is a multiline_text field..."
        ]: "marié",
      },
      outputValue: null,
    });

    await submitBioAnswer("Je suis marié");

    const proposedValueContainer = screen.getByText("proposedValueLabel").parentElement;
    expect(proposedValueContainer?.textContent).not.toContain("translates to");
    expect(proposedValueContainer?.textContent).not.toContain("{");
    expect(screen.queryByText(/translates to/i)).not.toBeInTheDocument();
  });

  it("shows a safe (blank) fallback instead of raw JSON when normalizedValue is an unexpected shape and outputValue is missing", async () => {
    submitAnswerMock.mockResolvedValue({
      id: "answer-1",
      status: "awaiting_confirmation",
      requiresClarification: false,
      validationStatus: "valid",
      originalAnswer: "Je suis marié",
      normalizedValue: { unexpectedKey: { nested: "garbage" } },
      outputValue: null,
    });

    await submitBioAnswer("Je suis marié");

    expect(screen.queryByText(/unexpectedKey/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/nested/i)).not.toBeInTheDocument();
    expect(document.body.textContent).not.toContain("[object Object]");
  });

  it("still renders a friendly summary for a documented structured field type (money)", async () => {
    getCurrentFieldMock.mockResolvedValue({ ...BIO_FIELD, fieldType: "money" });
    submitAnswerMock.mockResolvedValue({
      id: "answer-1",
      status: "awaiting_confirmation",
      requiresClarification: false,
      validationStatus: "valid",
      originalAnswer: "1800 euros monthly",
      normalizedValue: { amount: 1800, currency: "EUR", period: "monthly" },
      outputValue: null,
    });

    await submitBioAnswer("1800 euros monthly");

    expect(screen.getByText("1800 EUR monthly")).toBeDefined();
  });
});
