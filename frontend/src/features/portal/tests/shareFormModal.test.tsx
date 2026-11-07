import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ShareFormModal } from "../components/ShareFormModal";

describe("ShareFormModal (Phase G4)", () => {
  const mockForm = {
    id: "form-123",
    key: "anmeldung-stuttgart",
    name: "Anmeldung einer Wohnung (§ 17 BMG)",
  };

  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when isOpen is false", () => {
    const { container } = render(
      <ShareFormModal
        isOpen={false}
        onClose={mockOnClose}
        form={mockForm}
        orgSlug="stadt-stuttgart"
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders permalink, QR preview, poster download, and embed snippet when open", () => {
    render(
      <ShareFormModal
        isOpen={true}
        onClose={mockOnClose}
        form={mockForm}
        orgSlug="stadt-stuttgart"
      />
    );

    expect(screen.getByText("Share Form & Counter QR Code")).toBeInTheDocument();
    expect(screen.getByText("Anmeldung einer Wohnung (§ 17 BMG)")).toBeInTheDocument();

    // Verify input contains form link
    const input = screen.getByDisplayValue(/\/f\/stadt-stuttgart\/anmeldung-stuttgart/i);
    expect(input).toBeInTheDocument();

    // Verify QR code download links
    const pngDownloadLink = screen.getByRole("link", { name: /Download PNG/i });
    expect(pngDownloadLink).toHaveAttribute(
      "href",
      "/api/public/forms/anmeldung-stuttgart/qr?format=png"
    );

    const svgDownloadLink = screen.getByRole("link", { name: /Download SVG/i });
    expect(svgDownloadLink).toHaveAttribute(
      "href",
      "/api/public/forms/anmeldung-stuttgart/qr?format=svg"
    );

    // Verify counter poster PDF download link
    const posterLink = screen.getByRole("link", { name: /Download Poster PDF/i });
    expect(posterLink).toHaveAttribute(
      "href",
      "/api/public/forms/anmeldung-stuttgart/counter-poster.pdf"
    );

    // Verify embed code snippet
    expect(screen.getAllByText(/Anmeldung einer Wohnung/i).length).toBeGreaterThanOrEqual(2);
  });

  it("copies direct permalink to clipboard on button click", async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    render(
      <ShareFormModal
        isOpen={true}
        onClose={mockOnClose}
        form={mockForm}
        orgSlug="stadt-stuttgart"
      />
    );

    const copyBtn = screen.getByRole("button", { name: /Copy Link/i });
    fireEvent.click(copyBtn);

    await waitFor(() => {
      expect(writeTextMock).toHaveBeenCalledWith(
        expect.stringContaining("/f/stadt-stuttgart/anmeldung-stuttgart")
      );
      expect(screen.getByText("Copied!")).toBeInTheDocument();
    });
  });

  it("calls onClose when close button is clicked", () => {
    render(
      <ShareFormModal
        isOpen={true}
        onClose={mockOnClose}
        form={mockForm}
        orgSlug="stadt-stuttgart"
      />
    );

    const closeBtn = screen.getByRole("button", { name: "Close" });
    fireEvent.click(closeBtn);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });
});
