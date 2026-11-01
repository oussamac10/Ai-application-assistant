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

vi.mock("@/features/auth/context/AuthProvider", () => ({
  useAuth: () => ({ user: null, loading: false, login: vi.fn(), register: vi.fn(), logout: vi.fn(), refresh: vi.fn() }),
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

const CATEGORY_FIELD = {
  fieldId: "field-category",
  fieldKey: "request_category",
  id: "field-category",
  key: "request_category",
  fieldType: "multiple_choice",
  required: true,
  position: 1,
  label: "Request category",
  helpText: null,
  placeholder: null,
  options: [
    { value: "Housing", label: "Housing" },
    { value: "Education", label: "Education" },
    { value: "Medical", label: "Medical" },
  ],
  currentAnswerStatus: null,
  progress: { confirmedRequiredFields: 0, totalRequiredFields: 2, percentage: 0 },
};

const NEXT_FIELD = {
  ...CATEGORY_FIELD,
  fieldId: "field-next",
  key: "next_field",
  fieldKey: "next_field",
  fieldType: "string",
  position: 2,
  label: "Next field",
  options: null,
  progress: { confirmedRequiredFields: 1, totalRequiredFields: 2, percentage: 50 },
};

describe("Guided session — multiple_choice submit and advance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    startSessionMock.mockResolvedValue({ status: "in_progress" });
    getCurrentFieldMock.mockResolvedValue(CATEGORY_FIELD);
    getSummaryMock.mockRejectedValue(new Error("no summary yet"));
  });

  afterEach(() => {
    vi.resetModules();
  });

  it("displays every detected option for a dynamically generated multiple_choice question", async () => {
    const { default: GuidedSession } = await import(
      "@/app/application/session/[sessionId]/page"
    );
    render(<GuidedSession />);

    await waitFor(() => expect(screen.getByText("Request category")).toBeDefined());

    expect(screen.getByLabelText("Housing")).toBeDefined();
    expect(screen.getByLabelText("Education")).toBeDefined();
    expect(screen.getByLabelText("Medical")).toBeDefined();
  });

  it("selects options, submits, confirms, and advances to the next question", async () => {
    submitAnswerMock.mockResolvedValue({
      id: "answer-1",
      status: "awaiting_confirmation",
      requiresClarification: false,
      validationStatus: "valid",
      originalAnswer: '["Housing","Education"]',
      normalizedValue: ["Housing", "Education"],
      outputValue: "Housing, Education",
    });
    confirmAnswerMock.mockResolvedValue({
      id: "answer-1",
      status: "confirmed",
      requiresClarification: false,
      validationStatus: "valid",
      originalAnswer: '["Housing","Education"]',
    });

    const { default: GuidedSession } = await import(
      "@/app/application/session/[sessionId]/page"
    );
    render(<GuidedSession />);

    await waitFor(() => expect(screen.getByText("Request category")).toBeDefined());

    fireEvent.click(screen.getByLabelText("Housing"));
    fireEvent.click(screen.getByLabelText("Education"));

    fireEvent.click(screen.getByText("continue"));

    await waitFor(() =>
      expect(submitAnswerMock).toHaveBeenCalledWith(
        "session-1",
        "field-category",
        JSON.stringify(["Housing", "Education"])
      )
    );

    // Reaching "awaiting_confirmation" surfaces the existing, already-visible
    // confirm screen rather than a hidden second step.
    await waitFor(() => expect(screen.getByText("confirmTitle")).toBeDefined());

    getCurrentFieldMock.mockResolvedValue(NEXT_FIELD);
    fireEvent.click(screen.getByText("confirm"));

    await waitFor(() => expect(confirmAnswerMock).toHaveBeenCalledWith("session-1", "answer-1"));
    await waitFor(() => expect(screen.getByText("Next field")).toBeDefined());
  });

  it("surfaces an error and does not advance when an option is rejected as invalid", async () => {
    submitAnswerMock.mockResolvedValue({
      id: "answer-1",
      status: "draft",
      requiresClarification: false,
      validationStatus: "invalid",
      originalAnswer: '["Housing","NotAnOption"]',
      normalizedValue: ["Housing", "NotAnOption"],
      outputValue: null,
    });

    const { default: GuidedSession } = await import(
      "@/app/application/session/[sessionId]/page"
    );
    render(<GuidedSession />);

    await waitFor(() => expect(screen.getByText("Request category")).toBeDefined());
    fireEvent.click(screen.getByLabelText("Housing"));
    fireEvent.click(screen.getByText("continue"));

    await waitFor(() => expect(submitAnswerMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.getAllByText("invalidAnswer").length).toBeGreaterThan(0));

    // Still on the answering step — did not silently advance.
    expect(screen.getByText("Request category")).toBeDefined();
    expect(confirmAnswerMock).not.toHaveBeenCalled();
  });

  it("does not call /start twice under a duplicate mount (React StrictMode double effect)", async () => {
    const { default: GuidedSession } = await import(
      "@/app/application/session/[sessionId]/page"
    );

    render(
      <React.StrictMode>
        <GuidedSession />
      </React.StrictMode>
    );

    await waitFor(() => expect(screen.getByText("Request category")).toBeDefined());

    expect(startSessionMock).toHaveBeenCalledTimes(1);
  });

  it("treats an already-started session (409 from /start) as a safe no-op", async () => {
    const conflict = Object.assign(new Error("conflict"), { status: 409 });
    startSessionMock.mockRejectedValue(conflict);

    const { default: GuidedSession } = await import(
      "@/app/application/session/[sessionId]/page"
    );
    render(<GuidedSession />);

    await waitFor(() => expect(screen.getByText("Request category")).toBeDefined());
    expect(screen.queryByText("Error Occurred")).toBeNull();
  });

  it("displays translated choice labels while submitting canonical option values", async () => {
    getCurrentFieldMock.mockResolvedValue({
      ...CATEGORY_FIELD,
      label: "Wie lautet Ihr Anliegen?",
      options: [
        { value: "Housing", label: "Wohnen" },
        { value: "Education", label: "Bildung" },
        { value: "Medical", label: "Medizinisch" },
      ],
    });
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
    expect(screen.queryByLabelText("Housing")).toBeNull();

    fireEvent.click(screen.getByLabelText("Wohnen"));
    fireEvent.click(screen.getByLabelText("Bildung"));
    fireEvent.click(screen.getByText("continue"));

    await waitFor(() =>
      expect(submitAnswerMock).toHaveBeenCalledWith(
        "session-1",
        "field-category",
        JSON.stringify(["Housing", "Education"]),
      ),
    );
  });

  it("disables Back on the first dynamic question when position is 0", async () => {
    getCurrentFieldMock.mockResolvedValue({
      ...CATEGORY_FIELD,
      position: 0,
      allFieldKeys: ["request_category", "next_field"],
    });

    const { default: GuidedSession } = await import(
      "@/app/application/session/[sessionId]/page"
    );
    render(<GuidedSession />);

    await waitFor(() => expect(screen.getByText("Request category")).toBeDefined());
    const backBtn = screen.getByRole("button", { name: "back" });
    expect(backBtn).toBeDisabled();
  });
});
