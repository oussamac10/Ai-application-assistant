import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

/** The requiredness label and the Skip button, across all three states.
 *
 * The page used to render an unconditional paragraph:
 *
 *     {currentField.required ? t("required") : t("optional")}
 *
 * so every field the form said nothing about was labelled "Optional" — a claim
 * the document never made — and the boolean it read could not have expressed
 * anything else. Skip keyed off the same boolean, which happened to be right,
 * but for the wrong reason. */

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ sessionId: "session-1" }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) =>
    key === "rowFieldProgress" ? `${values?.position}/${values?.total}` : key,
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
const getSummaryMock = vi.fn();

vi.mock("@/features/form-session/services/apiClient", () => ({
  startSession: (...args: unknown[]) => startSessionMock(...args),
  getCurrentField: (...args: unknown[]) => getCurrentFieldMock(...args),
  submitAnswer: vi.fn(),
  submitClarification: vi.fn(),
  confirmAnswer: vi.fn(),
  previousField: vi.fn(),
  changeAnswer: vi.fn(),
  skipField: vi.fn(),
  getSummary: (...args: unknown[]) => getSummaryMock(...args),
}));

function field(overrides: Record<string, unknown>) {
  return {
    fieldId: "field-1",
    fieldKey: "nom_de_famille",
    id: "field-1",
    key: "nom_de_famille",
    fieldType: "string",
    required: false,
    position: 1,
    label: "Nom de famille",
    helpText: null,
    placeholder: null,
    options: null,
    currentAnswerStatus: null,
    progress: {
      confirmedRequiredFields: 0,
      totalRequiredFields: 0,
      totalQuestions: 3,
      answeredQuestions: 0,
      percentage: 0,
    },
    ...overrides,
  };
}

async function renderWith(fieldData: Record<string, unknown>) {
  getCurrentFieldMock.mockResolvedValue(fieldData);
  const { default: GuidedSession } = await import(
    "@/app/application/session/[sessionId]/page"
  );
  render(<GuidedSession />);
  await waitFor(() =>
    expect(screen.getByText(String(fieldData.label))).toBeTruthy(),
  );
}

describe("Guided session — three-state requiredness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    startSessionMock.mockResolvedValue({ status: "in_progress" });
    getSummaryMock.mockRejectedValue(new Error("no summary yet"));
  });

  afterEach(() => {
    vi.resetModules();
  });

  it("shows Required for an explicitly required question", async () => {
    await renderWith(field({ requiredness: "required", required: true }));

    expect(screen.getByTestId("requiredness").textContent).toBe("required");
  });

  it("shows Optional for an explicitly optional question", async () => {
    await renderWith(field({ requiredness: "optional" }));

    expect(screen.getByTestId("requiredness").textContent).toBe("optional");
  });

  it("shows no requiredness label at all when the document said nothing", async () => {
    await renderWith(field({ requiredness: "unknown" }));

    expect(screen.queryByTestId("requiredness")).toBeNull();
  });

  it("offers Skip for an unknown question — unknown does not mean required", async () => {
    await renderWith(field({ requiredness: "unknown" }));

    expect(screen.getByTestId("skip-question")).toBeTruthy();
  });

  it("offers Skip for an optional question", async () => {
    await renderWith(field({ requiredness: "optional" }));

    expect(screen.getByTestId("skip-question")).toBeTruthy();
  });

  it("does not offer Skip for an explicitly required question", async () => {
    await renderWith(field({ requiredness: "required", required: true }));

    expect(screen.queryByTestId("skip-question")).toBeNull();
  });

  it("keeps Skip enabled while the input is empty", async () => {
    // Skipping is what a user does *instead* of typing, so the button must
    // never be tied to the input value.
    await renderWith(field({ requiredness: "unknown" }));

    expect(
      (screen.getByTestId("skip-question") as HTMLButtonElement).disabled,
    ).toBe(false);
  });

  it("treats a response without requiredness as unknown, not optional", async () => {
    // A backend that has not been redeployed omits the field. Reading the
    // legacy boolean as "optional" would resurrect the false claim.
    await renderWith(field({ required: false }));

    expect(screen.queryByTestId("requiredness")).toBeNull();
    expect(screen.getByTestId("skip-question")).toBeTruthy();
  });

  it("populates existing answer and row progress from current-field without calling getSummary", async () => {
    await renderWith(
      field({
        fieldKey: "children_1_gender",
        key: "children_1_gender",
        currentAnswerStatus: "awaiting_confirmation",
        originalAnswer: "weiblich",
        allFieldKeys: ["children_1_first_name", "children_1_gender"],
      }),
    );

    const input = screen.getByRole("textbox") as HTMLInputElement;
    expect(input.value).toBe("weiblich");
    expect(screen.getByTestId("row-progress").textContent).toBe("2/2");
    expect(getSummaryMock).not.toHaveBeenCalled();
  });
});
