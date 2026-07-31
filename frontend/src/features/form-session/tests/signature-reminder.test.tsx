import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

/**
 * The reminder before download.
 *
 * When a signature was deliberately deferred to paper, the exported PDF's
 * signature box is left blank on purpose — nothing is written into the official
 * form. That makes the ready-for-export screen the last moment the app can say
 * anything at all, so the reminder belongs here rather than in the document.
 *
 * It must never appear for someone who signed digitally: telling them to sign
 * again would suggest their signature did not take.
 */

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ sessionId: "session-1" }),
}));

// One stable function per namespace: the page lists translators in effect
// dependency arrays, and a fresh function each render re-runs them forever.
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

const getSessionMock = vi.fn();
const getSummaryMock = vi.fn();

vi.mock("@/features/form-session/services/apiClient", () => ({
  getSession: (...args: unknown[]) => getSessionMock(...args),
  getSummary: (...args: unknown[]) => getSummaryMock(...args),
  createExport: vi.fn(),
  downloadExportBlob: vi.fn(),
  ExportResponse: {},
  ApiError: class extends Error {},
  TokenMissingError: class extends Error {},
}));

function summaryWith(answerState: string) {
  return {
    fields: [
      {
        fieldId: "f1",
        fieldKey: "nom",
        label: "Nom",
        required: false,
        originalAnswer: "Dupont",
        outputValue: "Dupont",
        status: "confirmed",
        answerState: "answered",
      },
      {
        fieldId: "f2",
        fieldKey: "signature",
        label: "Signature",
        required: true,
        requiredness: "required",
        originalAnswer: null,
        outputValue: null,
        status: answerState,
        answerState,
      },
    ],
  };
}

async function renderComplete() {
  const { default: SessionComplete } = await import(
    "@/app/application/session/[sessionId]/complete/page"
  );
  render(<SessionComplete />);
}

describe("Ready-for-export handwritten signature reminder", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getSessionMock.mockResolvedValue({ exportSupported: true });
  });

  afterEach(() => {
    vi.resetModules();
  });

  it("shows the reminder when a signature will be provided on paper", async () => {
    getSummaryMock.mockResolvedValue(summaryWith("pending_manual_signature"));

    await renderComplete();

    await waitFor(() =>
      expect(screen.getByTestId("handwritten-signature-reminder")).toBeTruthy(),
    );
  });

  it("shows no reminder when every signature was drawn in the app", async () => {
    getSummaryMock.mockResolvedValue(summaryWith("answered"));

    await renderComplete();

    await waitFor(() => expect(getSummaryMock).toHaveBeenCalled());
    expect(screen.queryByTestId("handwritten-signature-reminder")).toBeNull();
  });

  it("announces the reminder to assistive technology", async () => {
    getSummaryMock.mockResolvedValue(summaryWith("pending_manual_signature"));

    await renderComplete();

    await waitFor(() =>
      expect(
        screen.getByTestId("handwritten-signature-reminder").getAttribute("role"),
      ).toBe("status"),
    );
  });

  it("does not block the export when the summary cannot be read", async () => {
    // A summary we cannot load is not a reason to stop someone downloading,
    // and showing the reminder speculatively would be wrong for a digital
    // signer.
    getSummaryMock.mockRejectedValue(new Error("nope"));

    await renderComplete();

    await waitFor(() => expect(getSessionMock).toHaveBeenCalled());
    expect(screen.queryByTestId("handwritten-signature-reminder")).toBeNull();
  });
});
