import { render, screen, act } from "@testing-library/react";
import { expect, test, vi, beforeEach } from "vitest";
import Home from "./page";
import { checkBackendHealth, checkDatabaseHealth } from "@/services/api";

// Mock the api service module
vi.mock("@/services/api", () => ({
  checkBackendHealth: vi.fn(),
  checkDatabaseHealth: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

test("renders page title and header", async () => {
  vi.mocked(checkBackendHealth).mockResolvedValue(false);
  vi.mocked(checkDatabaseHealth).mockResolvedValue({ status: "error", database: "unavailable" });

  await act(async () => {
    render(<Home />);
  });

  expect(screen.getByText("AI Form Assistant")).toBeInTheDocument();
  expect(screen.getByText("Phase 1 Monorepo Foundation")).toBeInTheDocument();
});

test("displays loading state initially", async () => {
  // Let the health check promise hang to stay in loading state
  let resolveHealth: (value: boolean) => void = () => {};
  const healthPromise = new Promise<boolean>((resolve) => {
    resolveHealth = resolve;
  });
  vi.mocked(checkBackendHealth).mockReturnValue(healthPromise);

  render(<Home />);

  expect(screen.getByText("Checking backend connection")).toBeInTheDocument();

  // Cleanup/resolve to avoid memory leaks/hanging promises
  await act(async () => {
    resolveHealth(true);
  });
});

test("displays connected state when backend health check succeeds", async () => {
  vi.mocked(checkBackendHealth).mockResolvedValue(true);
  vi.mocked(checkDatabaseHealth).mockResolvedValue({ status: "ok", database: "connected" });

  await act(async () => {
    render(<Home />);
  });

  expect(screen.getByText("Backend connected")).toBeInTheDocument();
  expect(screen.getByText("Connected")).toBeInTheDocument();
});

test("displays unavailable state when backend health check fails", async () => {
  vi.mocked(checkBackendHealth).mockResolvedValue(false);
  vi.mocked(checkDatabaseHealth).mockResolvedValue({ status: "error", database: "unavailable" });

  await act(async () => {
    render(<Home />);
  });

  expect(screen.getByText("Backend unavailable")).toBeInTheDocument();
  expect(screen.getByText("Unavailable")).toBeInTheDocument();
});
