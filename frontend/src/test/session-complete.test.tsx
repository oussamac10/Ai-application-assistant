/**
 * Unit tests for the Phase 11 incorrect-export bug fix on the session
 * "complete" screen: dynamic (Phase 11 confirmed-field) sessions must never
 * show a PDF export button, and must show the safe unsupported-export
 * message instead. Predefined-template sessions must keep exporting as
 * before.
 */

import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ sessionId: "session-1" }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const mockUser = vi.fn<[], { id: string; email: string } | null>(() => null);

vi.mock("@/features/auth/hooks/useSafeAuth", () => ({
  useSafeAuth: () => {
    const user = mockUser();
    return user ? { user } : null;
  },
}));

const getSessionMock = vi.fn();
const createExportMock = vi.fn();

vi.mock("@/features/form-session/services/apiClient", () => ({
  getSession: (...args: unknown[]) => getSessionMock(...args),
  createExport: (...args: unknown[]) => createExportMock(...args),
  downloadExportBlob: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    detail: string | null;
    constructor(status: number, message: string, detail: string | null = null) {
      super(message);
      this.status = status;
      this.detail = detail;
    }
  },
  TokenMissingError: class TokenMissingError extends Error {},
}));

vi.mock("@/features/form-session/services/sessionCredentials", () => ({
  removeSessionToken: vi.fn(),
  getSessionToken: vi.fn(() => "mock-token"),
}));

vi.mock("@/features/applications/services/applicationClient", () => ({
  claimApplication: vi.fn().mockResolvedValue({ success: true }),
}));

async function renderComplete() {
  const { default: SessionComplete } = await import(
    "../app/application/session/[sessionId]/complete/page"
  );
  return render(<SessionComplete />);
}

describe("SessionComplete — dynamic vs predefined export gating", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("hides the export button and shows the unsupported message for a dynamic session", async () => {
    getSessionMock.mockResolvedValue({ exportSupported: false, formOrigin: "dynamic_detection" });

    await renderComplete();

    await waitFor(() => {
      expect(screen.getByText("dynamicExportUnsupported")).toBeInTheDocument();
    });
    expect(screen.queryByText("generatePdf")).not.toBeInTheDocument();
  });

  it("shows the export button for a predefined-template session", async () => {
    getSessionMock.mockResolvedValue({ exportSupported: true, formOrigin: "predefined_template" });

    await renderComplete();

    await waitFor(() => {
      expect(screen.getByText("generatePdf")).toBeInTheDocument();
    });
    expect(screen.queryByText("dynamicExportUnsupported")).not.toBeInTheDocument();
  });

  it("defaults to allowing export if the session lookup fails", async () => {
    getSessionMock.mockRejectedValue(new Error("network error"));

    await renderComplete();

    await waitFor(() => {
      expect(screen.getByText("generatePdf")).toBeInTheDocument();
    });
  });

  it("always shows the start-new button regardless of export support", async () => {
    getSessionMock.mockResolvedValue({ exportSupported: false, formOrigin: "dynamic_detection" });

    await renderComplete();

    await waitFor(() => {
      expect(screen.getByText("startNew")).toBeInTheDocument();
    });
  });

  it("shows account required notice and opens ExportAccountGateModal when unauthenticated user clicks generatePdf", async () => {
    mockUser.mockReturnValue(null);
    getSessionMock.mockResolvedValue({ exportSupported: true, formOrigin: "predefined_template" });

    await renderComplete();

    await waitFor(() => {
      expect(screen.getByText("exportAccountRequiredTitle")).toBeInTheDocument();
      expect(screen.getByText("generatePdf")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("generatePdf"));

    await waitFor(() => {
      expect(screen.getByText("exportGateTitle")).toBeInTheDocument();
      expect(screen.getByText("exportGateRegisterBtn")).toBeInTheDocument();
    });

    expect(createExportMock).not.toHaveBeenCalled();
  });

  it("directly triggers createExport without modal when authenticated user clicks generatePdf", async () => {
    mockUser.mockReturnValue({ id: "user-123", email: "test@example.com" });
    getSessionMock.mockResolvedValue({ exportSupported: true, formOrigin: "predefined_template" });
    createExportMock.mockResolvedValue({ exportId: "export-1", downloadUrl: "/api/export/1" });

    await renderComplete();

    await waitFor(() => {
      expect(screen.queryByText("exportAccountRequiredTitle")).not.toBeInTheDocument();
      expect(screen.getByText("generatePdf")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("generatePdf"));

    await waitFor(() => {
      expect(createExportMock).toHaveBeenCalledWith("session-1");
    });
    expect(screen.queryByText("exportGateTitle")).not.toBeInTheDocument();
  });
});
