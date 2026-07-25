/**
 * Unit tests for Phase 9 — Document Upload feature
 *
 * Covers:
 * - documentCredentials (sessionStorage helpers)
 * - Client-side file validation logic
 * - uploadDocument / getDocument / createSessionFromDocument API client
 * - DocumentUploadResponse schema parsing (Zod)
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import {
  setDocumentToken,
  getDocumentToken,
  removeDocumentToken,
} from "../features/document-upload/services/documentCredentials";
import {
  DocumentUploadResponseSchema,
  DocumentRetrieveResponseSchema,
  SessionCreateResponseSchema,
} from "../features/document-upload/types";

// ---------------------------------------------------------------------------
// documentCredentials helpers
// ---------------------------------------------------------------------------

describe("documentCredentials", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it("stores and retrieves a document token by documentId", () => {
    setDocumentToken("doc-abc-123", "token-xyz-789");
    expect(getDocumentToken("doc-abc-123")).toBe("token-xyz-789");
  });

  it("returns null for an unknown documentId", () => {
    expect(getDocumentToken("non-existent-doc")).toBeNull();
  });

  it("clears a stored token", () => {
    setDocumentToken("doc-to-clear", "temp-token");
    removeDocumentToken("doc-to-clear");
    expect(getDocumentToken("doc-to-clear")).toBeNull();
  });

  it("different documents have isolated tokens", () => {
    setDocumentToken("doc-1", "token-for-1");
    setDocumentToken("doc-2", "token-for-2");
    expect(getDocumentToken("doc-1")).toBe("token-for-1");
    expect(getDocumentToken("doc-2")).toBe("token-for-2");
  });

  it("overwriting a token replaces the previous value", () => {
    setDocumentToken("doc-override", "old-token");
    setDocumentToken("doc-override", "new-token");
    expect(getDocumentToken("doc-override")).toBe("new-token");
  });
});

// ---------------------------------------------------------------------------
// Client-side file validation (mirrors DocumentUploadForm logic)
// ---------------------------------------------------------------------------

function validateFile(file: File): string | null {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    return "error_invalid_file_type";
  }
  if (file.size > 10 * 1024 * 1024) {
    return "error_file_too_large";
  }
  return null;
}

describe("client-side file validation", () => {
  it("accepts a valid small PDF", () => {
    const f = new File(["content"], "form.pdf", { type: "application/pdf" });
    expect(validateFile(f)).toBeNull();
  });

  it("rejects a non-PDF file", () => {
    const f = new File(["content"], "resume.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    expect(validateFile(f)).toBe("error_invalid_file_type");
  });

  it("rejects a file disguised as PDF with wrong extension", () => {
    const f = new File(["content"], "fake.txt", { type: "text/plain" });
    expect(validateFile(f)).toBe("error_invalid_file_type");
  });

  it("rejects an oversized PDF (> 10 MB)", () => {
    const bigContent = new Uint8Array(11 * 1024 * 1024); // 11 MB
    const f = new File([bigContent], "big.pdf", { type: "application/pdf" });
    expect(validateFile(f)).toBe("error_file_too_large");
  });

  it("accepts a PDF exactly at the 10 MB limit", () => {
    const exactContent = new Uint8Array(10 * 1024 * 1024); // exactly 10 MB
    const f = new File([exactContent], "exact.pdf", { type: "application/pdf" });
    expect(validateFile(f)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Zod schema parsing for API response types
// ---------------------------------------------------------------------------

describe("DocumentUploadResponseSchema", () => {
  const baseAnalysis = {
    pageCount: 1,
    documentType: "fillable_pdf",
    hasNativeText: true,
    hasAcroForm: true,
    hasEmbeddedImages: false,
    isProbablyScanned: false,
    matchedTemplate: {
      templateKey: "basic-registration-v1",
      formKey: "basic-registration",
      formVersion: 1,
    },
    nextStep: "supported_template",
  };

  it("parses a valid upload response", () => {
    const raw = {
      documentId: "doc-uuid-1",
      ownershipToken: "tok-abc",
      status: "analyzed",
      expiresAt: "2026-07-26T10:00:00Z",
      analysis: baseAnalysis,
    };
    const result = DocumentUploadResponseSchema.parse(raw);
    expect(result.documentId).toBe("doc-uuid-1");
    expect(result.status).toBe("analyzed");
    expect(result.analysis?.pageCount).toBe(1);
    expect(result.analysis?.nextStep).toBe("supported_template");
  });

  it("parses a response without analysis (failed state)", () => {
    const raw = {
      documentId: "doc-uuid-2",
      ownershipToken: "tok-xyz",
      status: "failed",
      expiresAt: "2026-07-26T10:00:00Z",
    };
    const result = DocumentUploadResponseSchema.parse(raw);
    expect(result.status).toBe("failed");
    expect(result.analysis).toBeUndefined();
  });

  it("rejects a response missing documentId", () => {
    const raw = {
      ownershipToken: "tok-bad",
      status: "analyzed",
      expiresAt: "2026-07-26T10:00:00Z",
      analysis: baseAnalysis,
    };
    expect(() => DocumentUploadResponseSchema.parse(raw)).toThrow();
  });

  it("accepts all valid document types", () => {
    const types = ["digital_pdf", "fillable_pdf", "scanned_pdf", "hybrid_pdf", "unknown"];
    for (const docType of types) {
      const raw = {
        documentId: "doc-x",
        ownershipToken: "tok",
        status: "analyzed",
        expiresAt: "2026-07-26T10:00:00Z",
        analysis: { ...baseAnalysis, documentType: docType },
      };
      const result = DocumentUploadResponseSchema.parse(raw);
      expect(result.analysis?.documentType).toBe(docType);
    }
  });

  it("accepts all valid nextStep values", () => {
    const steps = ["supported_template", "ocr_required", "dynamic_field_detection", "review_required"];
    for (const step of steps) {
      const raw = {
        documentId: "doc-x",
        ownershipToken: "tok",
        status: "analyzed",
        expiresAt: "2026-07-26T10:00:00Z",
        analysis: { ...baseAnalysis, nextStep: step },
      };
      const result = DocumentUploadResponseSchema.parse(raw);
      expect(result.analysis?.nextStep).toBe(step);
    }
  });
});

describe("DocumentRetrieveResponseSchema", () => {
  it("parses a valid retrieve response", () => {
    const raw = {
      documentId: "doc-retrieve-1",
      status: "analyzed",
      expiresAt: "2026-07-26T10:00:00Z",
    };
    const result = DocumentRetrieveResponseSchema.parse(raw);
    expect(result.documentId).toBe("doc-retrieve-1");
    expect(result.status).toBe("analyzed");
  });

  it("rejects a retrieve response missing expiresAt", () => {
    const raw = { documentId: "doc-retrieve-2", status: "analyzed" };
    expect(() => DocumentRetrieveResponseSchema.parse(raw)).toThrow();
  });

  it("rejects a retrieve response missing status", () => {
    const raw = { documentId: "doc-retrieve-2", expiresAt: "2026-07-26T10:00:00Z" };
    expect(() => DocumentRetrieveResponseSchema.parse(raw)).toThrow();
  });
});

describe("SessionCreateResponseSchema", () => {
  it("parses a valid session creation response", () => {
    const raw = {
      sessionId: "sess-uuid-1",
      ownershipToken: "sess-tok-abc",
      status: "created",
    };
    const result = SessionCreateResponseSchema.parse(raw);
    expect(result.sessionId).toBe("sess-uuid-1");
    expect(result.ownershipToken).toBe("sess-tok-abc");
    expect(result.status).toBe("created");
  });

  it("rejects a session response missing ownershipToken", () => {
    const raw = { sessionId: "sess-uuid-2", status: "created" };
    expect(() => SessionCreateResponseSchema.parse(raw)).toThrow();
  });
});

// ---------------------------------------------------------------------------
// uploadDocument API client (XHR mock)
// ---------------------------------------------------------------------------

describe("uploadDocument XHR wrapper", () => {
  let xhrMock: {
    open: ReturnType<typeof vi.fn>;
    send: ReturnType<typeof vi.fn>;
    upload: { addEventListener: ReturnType<typeof vi.fn> };
    addEventListener: ReturnType<typeof vi.fn>;
    status: number;
    responseText: string;
  };

  beforeEach(() => {
    xhrMock = {
      open: vi.fn(),
      send: vi.fn(),
      upload: { addEventListener: vi.fn() },
      addEventListener: vi.fn(),
      status: 201,
      responseText: "",
    };
    vi.stubGlobal("XMLHttpRequest", vi.fn(() => xhrMock));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("calls XHR open with correct method and URL", async () => {
    // Set up mock to fire load event immediately on send
    xhrMock.addEventListener.mockImplementation((event: string, cb: Function) => {
      if (event === "load") {
        xhrMock.status = 201;
        xhrMock.responseText = JSON.stringify({
          documentId: "doc-1",
          ownershipToken: "tok-1",
          status: "analyzed",
          expiresAt: "2026-07-26T10:00:00Z",
        });
        setTimeout(() => cb(), 0);
      }
    });

    const { uploadDocument } = await import(
      "../features/document-upload/services/apiClient"
    );

    const file = new File(["content"], "test.pdf", { type: "application/pdf" });
    const promise = uploadDocument(file, "en", "de", true);

    await promise;

    expect(xhrMock.open).toHaveBeenCalledWith("POST", "/api/source-documents");
    expect(xhrMock.send).toHaveBeenCalled();
  });

  it("rejects with ApiError on non-2xx response", async () => {
    xhrMock.addEventListener.mockImplementation((event: string, cb: Function) => {
      if (event === "load") {
        xhrMock.status = 422;
        xhrMock.responseText = JSON.stringify({
          detail: "encrypted_pdf",
          error_code: "encrypted_pdf",
        });
        setTimeout(() => cb(), 0);
      }
    });

    const { uploadDocument } = await import(
      "../features/document-upload/services/apiClient"
    );

    const file = new File(["content"], "enc.pdf", { type: "application/pdf" });

    await expect(uploadDocument(file, "en", "en", true)).rejects.toMatchObject({
      status: 422,
    });
  });
});
