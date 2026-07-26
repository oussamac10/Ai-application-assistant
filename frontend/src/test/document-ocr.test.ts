/**
 * Unit tests for Phase 10 — Document OCR feature
 *
 * Covers:
 * - OcrResultResponseSchema parsing (Zod)
 * - requestOcr / getOcrResult API client (fetch mock)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { OcrResultResponseSchema } from "../features/document-ocr/types";
import { setDocumentToken } from "../features/document-upload/services/documentCredentials";

describe("OcrResultResponseSchema", () => {
  it("parses a completed OCR result with pages", () => {
    const parsed = OcrResultResponseSchema.parse({
      documentId: "doc-1",
      status: "completed",
      provider: "mock",
      language: "en",
      pageCount: 1,
      pages: [
        {
          pageNumber: 1,
          width: 2480,
          height: 3508,
          text: "Mock OCR page 1 (en)",
          averageConfidence: 95,
          lines: [
            {
              text: "Mock OCR page 1 (en)",
              confidence: 95,
              boundingBox: { x: 100, y: 200, width: 300, height: 40 },
              words: [
                {
                  text: "Mock",
                  confidence: 95,
                  boundingBox: { x: 100, y: 200, width: 80, height: 40 },
                },
              ],
            },
          ],
        },
      ],
      errorCode: null,
      expiresAt: "2026-07-27T10:00:00Z",
    });

    expect(parsed.status).toBe("completed");
    expect(parsed.pages).toHaveLength(1);
    expect(parsed.pages[0].lines[0].words[0].text).toBe("Mock");
  });

  it("parses a processing result with no pages yet", () => {
    const parsed = OcrResultResponseSchema.parse({
      documentId: "doc-2",
      status: "processing",
      language: "en",
      pages: [],
      expiresAt: "2026-07-27T10:00:00Z",
    });

    expect(parsed.status).toBe("processing");
    expect(parsed.pages).toEqual([]);
  });

  it("rejects a result missing documentId", () => {
    expect(() =>
      OcrResultResponseSchema.parse({
        status: "completed",
        language: "en",
        pages: [],
        expiresAt: "2026-07-27T10:00:00Z",
      })
    ).toThrow();
  });
});

describe("requestOcr / getOcrResult API client", () => {
  beforeEach(() => {
    sessionStorage.clear();
    setDocumentToken("doc-1", "test-token");
  });

  afterEach(() => {
    sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("sends X-Document-Token header and language body on POST", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        documentId: "doc-1",
        status: "completed",
        provider: "mock",
        language: "en",
        pageCount: 1,
        pages: [],
        expiresAt: "2026-07-27T10:00:00Z",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { requestOcr } = await import("../features/document-ocr/services/apiClient");
    const result = await requestOcr("doc-1", "en");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/source-documents/doc-1/ocr",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-Document-Token": "test-token" }),
        body: JSON.stringify({ language: "en" }),
      })
    );
    expect(result.status).toBe("completed");
  });

  it("rejects with ApiError carrying the backend error_code on failure", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "Not eligible.", error_code: "ocr_not_required" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { requestOcr } = await import("../features/document-ocr/services/apiClient");

    await expect(requestOcr("doc-1", "en")).rejects.toMatchObject({
      status: 422,
      detail: "ocr_not_required",
    });
  });

  it("getOcrResult performs a GET with auth header", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        documentId: "doc-1",
        status: "completed",
        language: "en",
        pages: [],
        expiresAt: "2026-07-27T10:00:00Z",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { getOcrResult } = await import("../features/document-ocr/services/apiClient");
    await getOcrResult("doc-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/source-documents/doc-1/ocr",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({ "X-Document-Token": "test-token" }),
      })
    );
  });
});
