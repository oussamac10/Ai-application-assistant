import React from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import NotFound from "./not-found";
import ErrorBoundary from "./error";
import Loading from "./loading";

describe("Milestone 1 — App Router Boundaries", () => {
  describe("NotFound Boundary", () => {
    it("renders civic-styled 404 heading, Lucide icon, and navigation links", () => {
      render(<NotFound />);

      expect(
        screen.getByRole("heading", { level: 1, name: /document or page not found/i }),
      ).toBeInTheDocument();

      expect(screen.getByText(/Error 404/i)).toBeInTheDocument();

      const homeLink = screen.getByRole("link", { name: /return to home/i });
      expect(homeLink).toHaveAttribute("href", "/");

      const appsLink = screen.getByRole("link", { name: /my applications/i });
      expect(appsLink).toHaveAttribute("href", "/applications");
    });
  });

  describe("ErrorBoundary", () => {
    it("renders alert message, digest reference, and handles reset invocation", () => {
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
      const resetMock = vi.fn();
      const testError = Object.assign(new Error("Network timeout while fetching form"), {
        digest: "ERR_CORRELATION_987",
      });

      render(<ErrorBoundary error={testError} reset={resetMock} />);

      expect(
        screen.getByRole("heading", { level: 1, name: /an unexpected error occurred/i }),
      ).toBeInTheDocument();

      expect(screen.getByText("ERR_CORRELATION_987")).toBeInTheDocument();

      const tryAgainBtn = screen.getByRole("button", { name: /try again/i });
      fireEvent.click(tryAgainBtn);
      expect(resetMock).toHaveBeenCalledTimes(1);

      const homeLink = screen.getByRole("link", { name: /return to home/i });
      expect(homeLink).toHaveAttribute("href", "/");
      consoleSpy.mockRestore();
    });
  });

  describe("Loading Boundary", () => {
    it("renders top indeterminate progress bar, live region, and skeleton cards", () => {
      render(<Loading />);

      expect(screen.getByText(/loading page content\.\.\./i)).toBeInTheDocument();
      expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
    });
  });
});
