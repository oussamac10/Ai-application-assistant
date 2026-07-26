/**
 * Unit tests for Phase 11 — Dynamic Field Detection feature
 *
 * Covers:
 * - FieldDetectionResultResponseSchema parsing (Zod)
 * - requestFieldDetection / getFieldDetectionResult / updateDetectedField /
 *   rejectDetectedField / createSessionFromFieldDetection API client
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { FieldDetectionResultResponseSchema } from "../features/field-detection/types";
import { setDocumentToken } from "../features/document-upload/services/documentCredentials";

describe("FieldDetectionResultResponseSchema", () => {
  it("parses a completed result with fields", () => {
    const parsed = FieldDetectionResultResponseSchema.parse({
      documentId: "doc-1",
      status: "completed",
      provider: "mock",
      sourceType: "native",
      fieldCount: 1,
      averageConfidence: 0.93,
      fields: [
        {
          fieldId: "field-1",
          pageNumber: 1,
          label: "Email",
          normalizedName: "email",
          fieldType: "email",
          required: null,
          multiple: false,
          confidence: 0.93,
          source: "native",
          labelBoundingBox: { x: 100, y: 200, width: 80, height: 20 },
          inputBoundingBox: null,
          options: [],
          existingValue: "john@example.com",
          reviewStatus: "pending_review",
        },
      ],
      errorCode: null,
      expiresAt: "2026-07-27T10:00:00Z",
    });

    expect(parsed.status).toBe("completed");
    expect(parsed.fields).toHaveLength(1);
    expect(parsed.fields[0].fieldType).toBe("email");
  });

  it("parses a processing result with no fields yet", () => {
    const parsed = FieldDetectionResultResponseSchema.parse({
      documentId: "doc-2",
      status: "processing",
      fields: [],
      expiresAt: "2026-07-27T10:00:00Z",
    });

    expect(parsed.status).toBe("processing");
    expect(parsed.fields).toEqual([]);
  });

  it("rejects a result missing documentId", () => {
    expect(() =>
      FieldDetectionResultResponseSchema.parse({
        status: "completed",
        fields: [],
        expiresAt: "2026-07-27T10:00:00Z",
      })
    ).toThrow();
  });
});

describe("field-detection API client", () => {
  beforeEach(() => {
    sessionStorage.clear();
    setDocumentToken("doc-1", "test-token");
  });

  afterEach(() => {
    sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("requestFieldDetection sends X-Document-Token header on POST", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        documentId: "doc-1",
        status: "completed",
        fields: [],
        expiresAt: "2026-07-27T10:00:00Z",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { requestFieldDetection } = await import(
      "../features/field-detection/services/apiClient"
    );
    const result = await requestFieldDetection("doc-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/source-documents/doc-1/field-detection",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-Document-Token": "test-token" }),
      })
    );
    expect(result.status).toBe("completed");
  });

  it("rejects with ApiError carrying the backend error_code on failure", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({
        detail: "Supported template.",
        error_code: "supported_template_detected",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { requestFieldDetection } = await import(
      "../features/field-detection/services/apiClient"
    );

    await expect(requestFieldDetection("doc-1")).rejects.toMatchObject({
      status: 422,
      detail: "supported_template_detected",
    });
  });

  it("updateDetectedField performs a PATCH with the given updates", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ fieldId: "field-1", reviewStatus: "confirmed" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { updateDetectedField } = await import(
      "../features/field-detection/services/apiClient"
    );
    await updateDetectedField("doc-1", "field-1", { reviewStatus: "confirmed" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/source-documents/doc-1/field-detection/fields/field-1",
      expect.objectContaining({
        method: "PATCH",
        headers: expect.objectContaining({ "X-Document-Token": "test-token" }),
        body: JSON.stringify({ reviewStatus: "confirmed" }),
      })
    );
  });

  it("rejectDetectedField performs a DELETE", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ fieldId: "field-1", reviewStatus: "rejected" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { rejectDetectedField } = await import(
      "../features/field-detection/services/apiClient"
    );
    await rejectDetectedField("doc-1", "field-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/source-documents/doc-1/field-detection/fields/field-1",
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("createSessionFromFieldDetection posts language + outputLanguage", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        sessionId: "session-1",
        ownershipToken: "tok",
        status: "created",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { createSessionFromFieldDetection } = await import(
      "../features/field-detection/services/apiClient"
    );
    const result = await createSessionFromFieldDetection("doc-1", "en", "de");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/source-documents/doc-1/field-detection/session",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ language: "en", outputLanguage: "de" }),
      })
    );
    expect(result.sessionId).toBe("session-1");
  });
});
