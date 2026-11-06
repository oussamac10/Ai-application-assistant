import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SaveAndResumeModal } from "../components/SaveAndResumeModal";
import ClaimBanner from "../components/ClaimBanner";
import * as applicationsClient from "../services/applicationsClient";
import * as sessionCredentials from "@/features/form-session/services/sessionCredentials";

const useSafeAuthMock = vi.fn();
vi.mock("@/features/auth/hooks/useSafeAuth", () => ({
  useSafeAuth: () => useSafeAuthMock(),
}));

const claimApplicationMock = vi.fn();
vi.mock("../services/applicationsClient", () => ({
  claimApplication: (...args: unknown[]) => claimApplicationMock(...args),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, unknown>) => {
    if (params) {
      return `${key} ${JSON.stringify(params)}`;
    }
    return key;
  },
}));

vi.mock("next/link", () => ({
  default: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

describe("Save & Resume Later — Progressive Onboarding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("SaveAndResumeModal", () => {
    it("does not render when isOpen is false", () => {
      render(
        <SaveAndResumeModal
          isOpen={false}
          onClose={vi.fn()}
          sessionId="sess-123"
          formTitle="Anmeldung Form"
        />
      );
      expect(screen.queryByRole("dialog")).toBeNull();
    });

    it("renders modal with progress details and redirect links to register & login", () => {
      const handleClose = vi.fn();
      render(
        <SaveAndResumeModal
          isOpen={true}
          onClose={handleClose}
          sessionId="sess-123"
          formTitle="Anmeldung Form"
          completedCount={4}
          totalCount={10}
          progressPercent={40}
        />
      );

      expect(screen.getByRole("dialog")).toBeDefined();
      expect(screen.getByText("Anmeldung Form")).toBeDefined();
      expect(screen.getByText("40%")).toBeDefined();

      // Register link with redirect
      const registerLink = screen.getByRole("link", { name: /createAccountToResume/i });
      expect(registerLink.getAttribute("href")).toBe(
        "/register?redirect=%2Fapplication%2Fsession%2Fsess-123"
      );

      // Login link with redirect
      const loginLink = screen.getByRole("link", { name: /loginToResume/i });
      expect(loginLink.getAttribute("href")).toBe(
        "/login?redirect=%2Fapplication%2Fsession%2Fsess-123"
      );

      // Dismiss on close button
      fireEvent.click(screen.getByText("continueAsGuest"));
      expect(handleClose).toHaveBeenCalled();
    });

    it("closes modal on Escape key press", () => {
      const handleClose = vi.fn();
      render(
        <SaveAndResumeModal
          isOpen={true}
          onClose={handleClose}
          sessionId="sess-123"
        />
      );

      fireEvent.keyDown(window, { key: "Escape" });
      expect(handleClose).toHaveBeenCalled();
    });
  });

  describe("ClaimBanner with Save & Resume Integration", () => {
    it("renders Save & Resume button for anonymous users and opens modal", () => {
      useSafeAuthMock.mockReturnValue({ user: null, loading: false });
      vi.spyOn(sessionCredentials, "getSessionToken").mockReturnValue("anon-token-abc");

      render(
        <ClaimBanner
          sessionId="sess-123"
          formTitle="Anmeldung Form"
          completedCount={2}
          totalCount={8}
          progressPercent={25}
        />
      );

      expect(screen.getByText("claimPromptTitle")).toBeDefined();
      const saveResumeBtn = screen.getByRole("button", { name: /saveAndResume/i });
      expect(saveResumeBtn).toBeDefined();

      // Click to open modal
      fireEvent.click(saveResumeBtn);
      expect(screen.getByRole("dialog")).toBeDefined();
    });

    it("auto-claims session when user is authenticated and token exists", async () => {
      useSafeAuthMock.mockReturnValue({
        user: { id: "user-1", email: "citizen@example.com" },
        loading: false,
      });
      vi.spyOn(sessionCredentials, "getSessionToken").mockReturnValue("anon-token-xyz");
      const removeTokenSpy = vi.spyOn(sessionCredentials, "removeSessionToken").mockReturnValue(undefined);
      claimApplicationMock.mockResolvedValue({
        id: "sess-123",
        title: "Claimed Form",
        status: "in_progress",
        form_name: "Anmeldung",
        form_origin: "predefined_template",
        export_supported: true,
        created_at: "2026-11-01T00:00:00Z",
        updated_at: "2026-11-01T00:00:00Z",
        last_opened_at: null,
      });

      render(<ClaimBanner sessionId="sess-123" />);

      await waitFor(() => {
        expect(claimApplicationMock).toHaveBeenCalledWith("sess-123", "anon-token-xyz");
        expect(removeTokenSpy).toHaveBeenCalledWith("sess-123");
        expect(screen.getByText("claimSuccess")).toBeDefined();
      });
    });
  });
});
