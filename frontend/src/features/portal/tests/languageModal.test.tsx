import React from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LanguageSelectionModal } from "../components/LanguageSelectionModal";

describe("LanguageSelectionModal", () => {
  it("renders when open and displays languages with search and regions", () => {
    const handleApply = vi.fn();
    const handleClose = vi.fn();

    render(
      <LanguageSelectionModal
        isOpen={true}
        onClose={handleClose}
        selectedLanguages={["de", "en"]}
        onApply={handleApply}
      />
    );

    expect(
      screen.getByText("Choose Supported Guidance Languages")
    ).toBeInTheDocument();
    expect(screen.getByText("Deutsch")).toBeInTheDocument();
    expect(screen.getByText("Italiano")).toBeInTheDocument();

    // Search for Italian
    const searchInput = screen.getByPlaceholderText(
      "Search by language, native name, code..."
    );
    fireEvent.change(searchInput, { target: { value: "Italian" } });

    expect(screen.getByText("Italiano")).toBeInTheDocument();
    expect(screen.queryByText("Deutsch")).not.toBeInTheDocument();

    // Toggle Italian
    fireEvent.click(screen.getByText("Italiano"));

    // Apply
    const applyBtn = screen.getByText(/Apply Selection/);
    fireEvent.click(applyBtn);

    expect(handleApply).toHaveBeenCalledWith(
      expect.arrayContaining(["de", "en", "it"])
    );
    expect(handleClose).toHaveBeenCalled();
  });
});
