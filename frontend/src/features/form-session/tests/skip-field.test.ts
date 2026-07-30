import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

/** `skipField` — the client half of skipping an optional question.
 *
 * The reported failure was that Skip did nothing: the page only re-fetched the
 * current field, and that endpoint returns the *stored* position, which nothing
 * had moved. Skipping is a real request to a dedicated endpoint, and repeated
 * clicks must not race two "advance" responses against each other.
 */

vi.mock("@/features/form-session/services/sessionCredentials", () => ({
  getSessionToken: () => "session-token",
}));
vi.mock("../services/sessionCredentials", () => ({
  getSessionToken: () => "session-token",
}));

const ANSWER = {
  id: "a1",
  fieldId: "f1",
  status: "skipped",
  validationStatus: "not_checked",
  requiresClarification: false,
  confirmedByUser: false,
  originalAnswer: null,
  normalizedValue: null,
  outputValue: null,
};

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

function ok() {
  return {
    ok: true,
    status: 200,
    json: async () => ANSWER,
  };
}

describe("skipField", () => {
  it("posts to the dedicated skip endpoint", async () => {
    const { skipField } = await import("../services/apiClient");
    fetchMock.mockResolvedValue(ok());

    const result = await skipField("session-1", "field-1");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/form-sessions/session-1/fields/field-1/skip");
    expect(init.method).toBe("POST");
    expect(result.status).toBe("skipped");
  });

  it("sends no answer body — a skip is not an empty answer", async () => {
    const { skipField } = await import("../services/apiClient");
    fetchMock.mockResolvedValue(ok());

    await skipField("session-1", "field-1");

    expect(fetchMock.mock.calls[0][1].body).toBeUndefined();
  });

  it("collapses repeated clicks into one request", async () => {
    const { skipField } = await import("../services/apiClient");
    let resolve!: (value: unknown) => void;
    fetchMock.mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    );

    const first = skipField("session-1", "field-1");
    const second = skipField("session-1", "field-1");
    const third = skipField("session-1", "field-1");

    expect(fetchMock).toHaveBeenCalledTimes(1);

    resolve(ok());
    const results = await Promise.all([first, second, third]);
    expect(results.every((r) => r.status === "skipped")).toBe(true);
  });

  it("skips different fields independently", async () => {
    const { skipField } = await import("../services/apiClient");
    fetchMock.mockResolvedValue(ok());

    await Promise.all([
      skipField("session-1", "field-1"),
      skipField("session-1", "field-2"),
    ]);

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("allows a retry after a failure", async () => {
    const { skipField } = await import("../services/apiClient");
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: "boom" }),
    });

    await expect(skipField("session-1", "field-1")).rejects.toBeTruthy();

    fetchMock.mockResolvedValueOnce(ok());
    const result = await skipField("session-1", "field-1");

    expect(result.status).toBe("skipped");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
