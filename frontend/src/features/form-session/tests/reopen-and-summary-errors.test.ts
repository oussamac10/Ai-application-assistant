import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

/** The client half of reopening a question and of a rejected confirmation.
 *
 * A 409 used to arrive as the single string "conflict", discarding the body —
 * so the page could only show a generic message even though the backend named
 * every blocking field. */

vi.mock("@/features/form-session/services/sessionCredentials", () => ({
  getSessionToken: () => "session-token",
}));
vi.mock("../services/sessionCredentials", () => ({
  getSessionToken: () => "session-token",
}));

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("reopenField", () => {
  it("posts to the reopen endpoint without a body", async () => {
    const { reopenField } = await import("../services/apiClient");
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ fieldId: "field-1", position: 3 }),
    });

    const result = await reopenField("session-1", "field-1");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/form-sessions/session-1/fields/field-1/reopen");
    expect(init.method).toBe("POST");
    // Reopening is navigation — it must never re-submit an answer, least of
    // all an empty one for a question that has none.
    expect(init.body).toBeUndefined();
    expect(result.position).toBe(3);
  });
});

describe("confirmSummary — structured rejection", () => {
  it("carries every blocking field through the ApiError", async () => {
    const { confirmSummary, ApiError } = await import("../services/apiClient");
    fetchMock.mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({
        code: "summary_not_confirmable",
        detail: "not confirmable",
        missing_required_fields: [
          { field_key: "signature", reason: "declaration_not_accepted" },
        ],
        invalid_answer_fields: [
          { field_key: "date_de_d_but_d_emploi", reason: "invalid_date" },
        ],
      }),
    });

    await expect(confirmSummary("session-1")).rejects.toMatchObject({
      status: 409,
      missingRequiredFields: [
        { fieldKey: "signature", reason: "declaration_not_accepted" },
      ],
      invalidAnswerFields: [
        { fieldKey: "date_de_d_but_d_emploi", reason: "invalid_date" },
      ],
    });

    await expect(confirmSummary("session-1")).rejects.toBeInstanceOf(ApiError);
  });

  it("tolerates a 409 that carries no field lists", async () => {
    const { confirmSummary } = await import("../services/apiClient");
    fetchMock.mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: "Session is not in progress." }),
    });

    await expect(confirmSummary("session-1")).rejects.toMatchObject({
      status: 409,
      missingRequiredFields: [],
      invalidAnswerFields: [],
    });
  });

  it("ignores malformed entries rather than surfacing undefined keys", async () => {
    const { confirmSummary } = await import("../services/apiClient");
    fetchMock.mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({
        missing_required_fields: [null, "nope", { reason: "no key" }],
        invalid_answer_fields: [{ field_key: "ok" }],
      }),
    });

    await expect(confirmSummary("session-1")).rejects.toMatchObject({
      missingRequiredFields: [],
      invalidAnswerFields: [{ fieldKey: "ok", reason: "invalid_value" }],
    });
  });
});
