import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

/**
 * An export refused for authorization reasons.
 *
 * The screen previously reacted to a 401 or 403 by redirecting into a brand new
 * session after three seconds. That destroys the work this screen is the *end*
 * of — every answer the user gave — in response to a problem they might be able
 * to resolve, and it does so before they have finished reading why.
 *
 * The failure is now reported in place. Retry is hidden because the ownership
 * state will not resolve by trying again; starting over remains available as
 * something the user chooses.
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
const createExportMock = vi.fn();

const { StubApiError, StubTokenMissingError } = vi.hoisted(() => ({
  StubApiError: class extends Error {
    constructor(
      public status: number,
      message: string,
      public detail: string | null = null,
    ) {
      super(message);
      this.name = "ApiError";
    }
  },
  StubTokenMissingError: class extends Error {},
}));

vi.mock("@/features/form-session/services/apiClient", () => ({
  ApiError: StubApiError,
  TokenMissingError: StubTokenMissingError,
  getSession: (...args: unknown[]) => getSessionMock(...args),
  getSummary: (...args: unknown[]) => getSummaryMock(...args),
  createExport: (...args: unknown[]) => createExportMock(...args),
  downloadExportBlob: vi.fn(),
}));

async function renderComplete() {
  const { default: SessionComplete } = await import(
    "@/app/application/session/[sessionId]/complete/page"
  );
  render(<SessionComplete />);
  await waitFor(() => expect(getSessionMock).toHaveBeenCalled());
}

async function attemptExport() {
  const button = await screen.findByText("generatePdf");
  fireEvent.click(button);
  await waitFor(() => expect(createExportMock).toHaveBeenCalled());
}

describe("Export refused for authorization reasons", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    getSessionMock.mockResolvedValue({ exportSupported: true });
    getSummaryMock.mockResolvedValue({ fields: [] });
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.resetModules();
  });

  it.each([401, 403])("shows the dedicated message for %s", async (status) => {
    createExportMock.mockRejectedValue(new StubApiError(status, "forbidden"));

    await renderComplete();
    await attemptExport();

    await waitFor(() =>
      expect(screen.getByText("error_export_forbidden")).toBeTruthy(),
    );
  });

  it.each([401, 403])("does not redirect after %s", async (status) => {
    createExportMock.mockRejectedValue(new StubApiError(status, "forbidden"));

    await renderComplete();
    await attemptExport();
    await waitFor(() =>
      expect(screen.getByText("error_export_forbidden")).toBeTruthy(),
    );

    // The old behaviour redirected after three seconds. Past that point the
    // user must still be here, with their work intact.
    vi.advanceTimersByTime(6000);

    expect(pushMock).not.toHaveBeenCalled();
  });

  it("keeps the ready-for-export screen mounted", async () => {
    createExportMock.mockRejectedValue(new StubApiError(403, "forbidden"));

    await renderComplete();
    await attemptExport();

    await waitFor(() =>
      expect(screen.getByText("error_export_forbidden")).toBeTruthy(),
    );
    // The page itself is still here, not replaced by a redirect placeholder.
    expect(screen.getByText("title")).toBeTruthy();
  });

  it("never starts a new session on the user's behalf", async () => {
    createExportMock.mockRejectedValue(new StubApiError(403, "forbidden"));

    await renderComplete();
    await attemptExport();
    vi.advanceTimersByTime(6000);

    // No navigation at all, so nothing can have created a session.
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("hides retry, because the ownership state will not change", async () => {
    createExportMock.mockRejectedValue(new StubApiError(403, "forbidden"));

    await renderComplete();
    await attemptExport();
    await waitFor(() =>
      expect(screen.getByText("error_export_forbidden")).toBeTruthy(),
    );

    expect(screen.queryByTestId("retry-export")).toBeNull();
  });

  it("leaves starting over available as a choice", async () => {
    createExportMock.mockRejectedValue(new StubApiError(403, "forbidden"));

    await renderComplete();
    await attemptExport();
    await waitFor(() =>
      expect(screen.getByText("error_export_forbidden")).toBeTruthy(),
    );

    // Present, but only acted on when the user decides.
    expect(screen.getByText("startNew")).toBeTruthy();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("never shows a token or backend detail", async () => {
    createExportMock.mockRejectedValue(
      new StubApiError(403, "forbidden", "token abc123 rejected at /srv/app"),
    );

    await renderComplete();
    await attemptExport();
    await waitFor(() =>
      expect(screen.getByText("error_export_forbidden")).toBeTruthy(),
    );

    const text = document.body.textContent ?? "";
    expect(text).not.toContain("abc123");
    expect(text).not.toContain("/srv/app");
  });
});
