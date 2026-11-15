import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { InviteSuccessModal } from "../components/InviteSuccessModal";
import type { Case } from "../types";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const LONG_GERMAN_FORM_TITLE =
  "Antrag Auf Erteilung Eines Wohnberechtigungsscheins Und Aufnahme In Die Vormerkdatei Fuer Stuttgarter Buerger. Barrierefrei";

const SAMPLE_CASE: Case = {
  id: "case-uuid-1",
  public_id: "case-pub-1",
  organization_id: "org-1",
  candidate_name: "Oussama Test",
  candidate_email: "applicant@example.org",
  status: "invited",
  form_version_id: "fv-1",
  form_title: LONG_GERMAN_FORM_TITLE,
  created_at: "2026-11-15T10:00:00Z",
  updated_at: "2026-11-15T10:00:00Z",
  invite_token: "6QER4D-TOKEN-99",
  total_fields: 12,
  answered_fields: 0,
  progress_percent: 0,
};

describe("InviteSuccessModal", () => {
  const originalClipboard = navigator.clipboard;

  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
      configurable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(navigator, "clipboard", {
      value: originalClipboard,
      configurable: true,
    });
  });

  it("returns null when caseData is missing or lacks an invite token", () => {
    const { container: c1 } = render(
      <InviteSuccessModal caseData={null} onClose={vi.fn()} />
    );
    expect(c1.firstChild).toBeNull();

    const { container: c2 } = render(
      <InviteSuccessModal
        caseData={{ ...SAMPLE_CASE, invite_token: null }}
        onClose={vi.fn()}
      />
    );
    expect(c2.firstChild).toBeNull();
  });

  it("renders dialog with applicant metadata and long German form title", () => {
    render(<InviteSuccessModal caseData={SAMPLE_CASE} onClose={vi.fn()} />);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("inviteModalTitle")).toBeInTheDocument();
    expect(screen.getByText("Oussama Test")).toBeInTheDocument();
    expect(screen.getByText("applicant@example.org")).toBeInTheDocument();
    expect(screen.getByText(LONG_GERMAN_FORM_TITLE)).toBeInTheDocument();

    const urlInput = screen.getByLabelText("Personal invite link") as HTMLInputElement;
    expect(urlInput.value).toContain("/portal/invite/6QER4D-TOKEN-99");
  });

  it("copies invite URL to clipboard and shows copied state", async () => {
    render(<InviteSuccessModal caseData={SAMPLE_CASE} onClose={vi.fn()} />);

    const copyBtn = screen.getByRole("button", { name: /copyInvite/i });
    fireEvent.click(copyBtn);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining("/portal/invite/6QER4D-TOKEN-99")
      );
      expect(screen.getByText("copied")).toBeInTheDocument();
    });
  });

  it("renders Send by Email mailto action and Open Preview link", () => {
    render(<InviteSuccessModal caseData={SAMPLE_CASE} onClose={vi.fn()} />);

    const emailLink = screen.getByRole("link", { name: /Send by Email/i });
    const href = emailLink.getAttribute("href") ?? "";
    expect(href).toContain("mailto:applicant@example.org");
    expect(href).toContain(
      `subject=${encodeURIComponent(`Form invitation: ${LONG_GERMAN_FORM_TITLE}`)}`
    );
    expect(href).toContain(encodeURIComponent("/portal/invite/6QER4D-TOKEN-99"));

    const previewLink = screen.getByRole("link", { name: /Open Preview/i });
    expect(previewLink).toHaveAttribute("target", "_blank");
    expect(previewLink).toHaveAttribute("rel", "noopener noreferrer");
    expect(previewLink.getAttribute("href")).toContain(
      "/portal/invite/6QER4D-TOKEN-99"
    );
  });

  it("closes via Done button, Close dialog button, and Escape key", () => {
    const onClose = vi.fn();
    render(<InviteSuccessModal caseData={SAMPLE_CASE} onClose={onClose} />);

    fireEvent.click(screen.getByRole("button", { name: "done" }));
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(onClose).toHaveBeenCalledTimes(2);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(3);
  });
});
