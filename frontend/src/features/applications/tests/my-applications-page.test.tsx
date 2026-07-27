import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const useAuthMock = vi.fn();
vi.mock("@/features/auth/context/AuthProvider", () => ({
  useAuth: () => useAuthMock(),
}));

const listApplicationsMock = vi.fn();
const renameApplicationMock = vi.fn();
const deleteApplicationMock = vi.fn();

vi.mock("@/features/applications/services/applicationsClient", () => ({
  listApplications: (...args: unknown[]) => listApplicationsMock(...args),
  renameApplication: (...args: unknown[]) => renameApplicationMock(...args),
  deleteApplication: (...args: unknown[]) => deleteApplicationMock(...args),
}));

const SAMPLE_APP = {
  id: "session-1",
  title: "My Visa Application",
  status: "in_progress",
  formName: "Basic Registration",
  formOrigin: "predefined_template",
  exportSupported: true,
  progressPercentage: 50,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-02T00:00:00Z",
  lastOpenedAt: null,
};

afterEach(() => {
  vi.clearAllMocks();
});

describe("My Applications page", () => {
  it("redirects to /login when the user is not authenticated", async () => {
    useAuthMock.mockReturnValue({ user: null, loading: false });
    const { default: MyApplicationsPage } = await import("@/app/applications/page");
    render(<MyApplicationsPage />);

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/login"));
  });

  it("lists saved applications for an authenticated user", async () => {
    useAuthMock.mockReturnValue({ user: { id: "u1", email: "user@example.com" }, loading: false });
    listApplicationsMock.mockResolvedValue([SAMPLE_APP]);

    const { default: MyApplicationsPage } = await import("@/app/applications/page");
    render(<MyApplicationsPage />);

    await waitFor(() => expect(screen.getByText("My Visa Application")).toBeDefined());
    expect(pushMock).not.toHaveBeenCalledWith("/login");
  });

  it("renames an application in place", async () => {
    useAuthMock.mockReturnValue({ user: { id: "u1", email: "user@example.com" }, loading: false });
    listApplicationsMock.mockResolvedValue([SAMPLE_APP]);
    renameApplicationMock.mockResolvedValue({ ...SAMPLE_APP, title: "Renamed Application" });

    const { default: MyApplicationsPage } = await import("@/app/applications/page");
    render(<MyApplicationsPage />);

    await waitFor(() => expect(screen.getByText("My Visa Application")).toBeDefined());

    fireEvent.click(screen.getByText("rename"));
    const input = await waitFor(() => screen.getByDisplayValue("My Visa Application"));
    fireEvent.change(input, { target: { value: "Renamed Application" } });
    fireEvent.click(screen.getByText("renameSave"));

    await waitFor(() =>
      expect(renameApplicationMock).toHaveBeenCalledWith("session-1", "Renamed Application")
    );
    await waitFor(() => expect(screen.queryByText("Renamed Application")).not.toBeNull());
  });

  it("deletes an application after confirmation", async () => {
    useAuthMock.mockReturnValue({ user: { id: "u1", email: "user@example.com" }, loading: false });
    listApplicationsMock.mockResolvedValue([SAMPLE_APP]);
    deleteApplicationMock.mockResolvedValue(undefined);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    const { default: MyApplicationsPage } = await import("@/app/applications/page");
    render(<MyApplicationsPage />);

    await waitFor(() => expect(screen.getByText("My Visa Application")).toBeDefined());
    fireEvent.click(screen.getByText("delete"));

    await waitFor(() => expect(confirmSpy).toHaveBeenCalled());
    await waitFor(() => expect(deleteApplicationMock).toHaveBeenCalledWith("session-1"));
    await waitFor(() => expect(screen.queryByText("My Visa Application")).toBeNull(), {
      timeout: 3000,
    });
  });
});
