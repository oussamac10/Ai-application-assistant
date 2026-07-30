import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

/** The summary must tell three absences apart.
 *
 * It previously showed "Missing required answer" for anything unconfirmed on a
 * field whose legacy boolean was true, and the raw backend `status` string
 * ("unanswered") for everything else — so a question deliberately skipped and
 * one never reached looked identical, and neither said what the user should do
 * about it. */

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ sessionId: "session-1" }),
}));

// One stable function per namespace: the page's load effect lists its
// translator in its dependency array, so a fresh function each render would
// re-run the effect forever and the page would never leave "loading".
const translators = new Map<string, (key: string) => string>();
vi.mock("next-intl", () => ({
  useTranslations: (namespace = "") => {
    if (!translators.has(namespace)) {
      translators.set(namespace, (key: string) => key);
    }
    return translators.get(namespace)!;
  },
}));

vi.mock("@/features/form-session/services/sessionCredentials", () => ({
  getSessionToken: () => "test-token",
  removeSessionToken: vi.fn(),
}));

const getSummaryMock = vi.fn();
const confirmSummaryMock = vi.fn();
const reopenFieldMock = vi.fn();

// The page narrows with `err instanceof ApiError`, so the class the test
// throws and the one the page imports must be the same object.
const { StubApiError } = vi.hoisted(() => ({
  StubApiError: class extends Error {
    constructor(
      public status: number,
      message: string,
      public detail: string | null = null,
      public missingRequiredFields: { fieldKey: string; reason: string }[] = [],
      public invalidAnswerFields: { fieldKey: string; reason: string }[] = [],
    ) {
      super(message);
      this.name = "ApiError";
    }
  },
}));

vi.mock("@/features/form-session/services/apiClient", () => ({
  ApiError: StubApiError,
  getSummary: (...args: unknown[]) => getSummaryMock(...args),
  confirmSummary: (...args: unknown[]) => confirmSummaryMock(...args),
  reopenField: (...args: unknown[]) => reopenFieldMock(...args),
  changeAnswer: vi.fn(),
}));

function row(overrides: Record<string, unknown>) {
  return {
    fieldId: "f-1",
    fieldKey: "k-1",
    label: "Label",
    required: false,
    requiredness: "unknown",
    originalAnswer: null,
    outputValue: null,
    status: "unanswered",
    answerState: "unreached",
    ...overrides,
  };
}

const SUMMARY = {
  fields: [
    row({
      fieldId: "f-answered",
      fieldKey: "nom",
      label: "Nom",
      status: "confirmed",
      answerState: "answered",
      originalAnswer: "Dupont",
      outputValue: "Dupont",
    }),
    row({
      fieldId: "f-skipped",
      fieldKey: "date_de_d_but_d_emploi",
      label: "Date de début d'emploi",
      requiredness: "optional",
      status: "skipped",
      answerState: "skipped",
    }),
    row({
      fieldId: "f-unknown",
      fieldKey: "deuxieme_prenom",
      label: "Deuxième prénom",
      requiredness: "unknown",
      answerState: "unanswered",
    }),
    row({
      fieldId: "f-required",
      fieldKey: "signature",
      label: "Signature",
      required: true,
      requiredness: "required",
      answerState: "unreached",
    }),
  ],
};

async function renderSummary() {
  const { default: SessionSummary } = await import(
    "@/app/application/session/[sessionId]/summary/page"
  );
  render(<SessionSummary />);
  await waitFor(() => expect(screen.getByText("Nom")).toBeTruthy());
}

describe("Summary — skipped, not answered, missing required", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSummaryMock.mockResolvedValue(SUMMARY);
    reopenFieldMock.mockResolvedValue({ fieldId: "f-skipped", position: 2 });
  });

  afterEach(() => {
    vi.resetModules();
  });

  it("labels a deliberately skipped question as Skipped", async () => {
    await renderSummary();

    expect(
      screen.getByTestId("summary-status-date_de_d_but_d_emploi").textContent,
    ).toBe("skipped");
  });

  it("labels an unanswered unknown question as Not answered, not Missing", async () => {
    await renderSummary();

    expect(screen.getByTestId("summary-status-deuxieme_prenom").textContent).toBe(
      "notAnswered",
    );
  });

  it("reserves Missing required answer for explicitly required questions", async () => {
    await renderSummary();

    expect(screen.getByTestId("summary-status-signature").textContent).toBe(
      "missingRequired",
    );
  });

  it("marks required questions with an asterisk and unknown ones without", async () => {
    await renderSummary();

    expect(screen.getByTestId("summary-row-signature").textContent).toContain("*");
    expect(
      screen.getByTestId("summary-row-deuxieme_prenom").textContent,
    ).not.toContain("*");
  });

  it("lets the user edit a skipped question", async () => {
    await renderSummary();

    const editButtons = screen.getAllByText("edit");
    fireEvent.click(editButtons[1]);

    await waitFor(() =>
      expect(reopenFieldMock).toHaveBeenCalledWith("session-1", "f-skipped"),
    );
    // Reopen is navigation: no answer is re-submitted, so a question with
    // nothing in it can be edited too.
    expect(pushMock).toHaveBeenCalledWith("/application/session/session-1");
  });

  it("does not block confirmation on optional or unknown questions alone", async () => {
    getSummaryMock.mockResolvedValue({
      fields: SUMMARY.fields.filter((f) => f.fieldKey !== "signature"),
    });
    confirmSummaryMock.mockResolvedValue({ status: "ready_for_export" });
    await renderSummary();

    const button = screen.getByText("submitSummary") as HTMLButtonElement;
    expect(button.disabled).toBe(false);

    fireEvent.click(button);
    await waitFor(() => expect(confirmSummaryMock).toHaveBeenCalled());
  });

  it("marks every blocking field named by a rejected confirmation", async () => {
    getSummaryMock.mockResolvedValue({
      fields: SUMMARY.fields.filter((f) => f.fieldKey !== "signature"),
    });
    confirmSummaryMock.mockRejectedValue(
      new StubApiError(409, "conflict", "not confirmable", [], [
        { fieldKey: "date_de_d_but_d_emploi", reason: "invalid_date" },
      ]),
    );
    await renderSummary();

    fireEvent.click(screen.getByText("submitSummary"));

    await waitFor(() =>
      expect(
        screen
          .getByTestId("summary-row-date_de_d_but_d_emploi")
          .className.includes("rose"),
      ).toBe(true),
    );
  });
});
