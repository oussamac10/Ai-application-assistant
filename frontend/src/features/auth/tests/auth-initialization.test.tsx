/**
 * Tests for GET /api/auth/me handling and auth initialization behavior.
 *
 * Covers:
 * - 401 from /me resolves to an anonymous (null) user, not an error
 * - 200 from /me sets the current user
 * - a real failure (500 / network error) still rejects as an error
 * - concurrent calls (e.g. React Strict Mode's double effect invocation)
 *   share one in-flight request instead of firing a duplicate fetch
 * - all auth requests are sent with credentials: "include"
 */
import React from "react";
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("authClient.getCurrentUser", () => {
  it("resolves to null (anonymous) on a 401, without throwing", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Authentication required." }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { getCurrentUser } = await import("../services/authClient");
    const result = await getCurrentUser();

    expect(result).toBeNull();
  });

  it("resolves to the parsed user on a 200", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: "user-1",
        email: "user@example.com",
        createdAt: "2026-01-01T00:00:00Z",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { getCurrentUser } = await import("../services/authClient");
    const result = await getCurrentUser();

    expect(result).toEqual({
      id: "user-1",
      email: "user@example.com",
      createdAt: "2026-01-01T00:00:00Z",
    });
  });

  it("rejects as a real error on a 500 response", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: "Internal server error." }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { getCurrentUser, AuthApiError } = await import("../services/authClient");

    await expect(getCurrentUser()).rejects.toBeInstanceOf(AuthApiError);
    await expect(getCurrentUser()).rejects.toMatchObject({ status: 500 });
  });

  it("rejects as a real error on a network failure", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    vi.stubGlobal("fetch", fetchMock);

    const { getCurrentUser } = await import("../services/authClient");

    await expect(getCurrentUser()).rejects.toThrow("Failed to fetch");
  });

  it("shares one in-flight request across concurrent callers (Strict Mode double effect)", async () => {
    let resolveFetch: (value: unknown) => void;
    const fetchMock = vi.fn().mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve;
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const { getCurrentUser } = await import("../services/authClient");

    // Two overlapping calls, as the two Strict-Mode effect invocations would make.
    const first = getCurrentUser();
    const second = getCurrentUser();

    resolveFetch!({
      ok: true,
      json: async () => ({ id: "user-1", email: "user@example.com", createdAt: "now" }),
    });

    const [firstResult, secondResult] = await Promise.all([first, second]);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(firstResult).toEqual(secondResult);
  });

  it("starts a fresh request for calls that do not overlap in time", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "user-1", email: "user@example.com", createdAt: "now" }),
      });
    vi.stubGlobal("fetch", fetchMock);

    const { getCurrentUser } = await import("../services/authClient");

    const anonymous = await getCurrentUser();
    const afterLogin = await getCurrentUser();

    expect(anonymous).toBeNull();
    expect(afterLogin).not.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("always sends credentials: include", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({}),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { getCurrentUser } = await import("../services/authClient");
    await getCurrentUser();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/me",
      expect.objectContaining({ credentials: "include" })
    );
  });
});

describe("AuthProvider initialization", () => {
  beforeEach(() => {
    vi.doMock("next-intl", () => ({
      useTranslations: () => (key: string) => key,
    }));
  });

  it("resolves to anonymous state (loading=false, user=null) on a 401, with no error banner", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({}),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { AuthProvider, useAuth } = await import("../context/AuthProvider");

    function Probe() {
      const { user, loading } = useAuth();
      return <div data-testid="probe">{loading ? "loading" : user ? "authed" : "anonymous"}</div>;
    }

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>
    );

    expect(screen.getByTestId("probe").textContent).toBe("loading");
    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("anonymous"));
  });

  it("is safe under a repeated (Strict-Mode-like) effect execution: only one network call, consistent final state", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "user-1", email: "user@example.com", createdAt: "now" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { AuthProvider, useAuth } = await import("../context/AuthProvider");

    function Probe() {
      const { user, loading } = useAuth();
      return <div data-testid="probe">{loading ? "loading" : user ? user.email : "anonymous"}</div>;
    }

    // React.StrictMode double-invokes effects (mount -> cleanup -> mount) in
    // development; rendering under it here exercises exactly that path.
    render(
      <React.StrictMode>
        <AuthProvider>
          <Probe />
        </AuthProvider>
      </React.StrictMode>
    );

    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("user@example.com"));
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
