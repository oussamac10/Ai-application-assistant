import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

/** Preparation takes tens of seconds (Azure/OCR plus AI translation), so a
 * duplicate in-flight request is expensive and lets two responses race to set
 * component state. React Strict Mode's double-invoked effects and an impatient
 * second click both produce one. */

vi.mock("@/features/document-upload/services/documentCredentials", () => ({
  getDocumentToken: () => "doc-token",
}));
vi.mock("../../document-upload/services/documentCredentials", () => ({
  getDocumentToken: () => "doc-token",
}));

const READY_RESPONSE = {
  documentId: "doc-1",
  status: "ready",
  sessionId: "session-1",
  ownershipToken: "session-token-1",
  reusedExistingSession: false,
  uncertainty: null,
  errorCode: null,
  stage: null,
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

function deferredResponse() {
  let resolve!: (value: unknown) => void;
  const promise = new Promise((r) => {
    resolve = r;
  });
  return {
    promise,
    settle: () =>
      resolve({
        ok: true,
        status: 200,
        json: async () => READY_RESPONSE,
      }),
  };
}

describe("prepareQuestions request de-duplication", () => {
  it("issues one request when called twice concurrently for the same document", async () => {
    const { prepareQuestions } = await import("../services/apiClient");
    const deferred = deferredResponse();
    fetchMock.mockReturnValue(deferred.promise);

    const first = prepareQuestions("doc-1", "en", "de");
    const second = prepareQuestions("doc-1", "en", "de");

    expect(fetchMock).toHaveBeenCalledTimes(1);

    deferred.settle();
    const [a, b] = await Promise.all([first, second]);

    // Both callers get the same result, so neither can act on stale data.
    expect(a.sessionId).toBe("session-1");
    expect(b.sessionId).toBe("session-1");
  });

  it("issues separate requests for different documents", async () => {
    const { prepareQuestions } = await import("../services/apiClient");
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => READY_RESPONSE,
    });

    await Promise.all([
      prepareQuestions("doc-1", "en", "de"),
      prepareQuestions("doc-2", "en", "de"),
    ]);

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("issues a separate request when the languages differ", async () => {
    const { prepareQuestions } = await import("../services/apiClient");
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => READY_RESPONSE,
    });

    await Promise.all([
      prepareQuestions("doc-1", "en", "de"),
      prepareQuestions("doc-1", "en", "fr"),
    ]);

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("allows a genuine retry after the first attempt fails", async () => {
    const { prepareQuestions } = await import("../services/apiClient");
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    });

    await expect(prepareQuestions("doc-1", "en", "de")).rejects.toBeTruthy();

    // The failed request must not be cached as in-flight forever.
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => READY_RESPONSE,
    });
    const result = await prepareQuestions("doc-1", "en", "de");

    expect(result.sessionId).toBe("session-1");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("allows a new request after a successful one settles", async () => {
    const { prepareQuestions } = await import("../services/apiClient");
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => READY_RESPONSE,
    });

    await prepareQuestions("doc-1", "en", "de");
    await prepareQuestions("doc-1", "en", "de");

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("polls GET /api/jobs/{jobId} when prepare-questions returns 202 Accepted until completed", async () => {
    const { prepareQuestions } = await import("../services/apiClient");
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 202,
        json: async () => ({
          documentId: "doc-1",
          status: "queued",
          jobId: "job-123",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          jobId: "job-123",
          documentId: "doc-1",
          jobType: "prepare_questions",
          status: "running",
          stage: "ocr",
          result: null,
          errorCode: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          jobId: "job-123",
          documentId: "doc-1",
          jobType: "prepare_questions",
          status: "completed",
          stage: null,
          result: READY_RESPONSE,
          errorCode: null,
        }),
      });

    const result = await prepareQuestions("doc-1", "ar", undefined, {
      pollIntervalMs: 5,
    });

    expect(result.sessionId).toBe("session-1");
    expect(result.ownershipToken).toBe("session-token-1");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/jobs/job-123");
  });
});
