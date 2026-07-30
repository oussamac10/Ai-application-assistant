import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const uploadDocumentMock = vi.fn();
vi.mock("../services/apiClient", () => ({
  uploadDocument: (...args: unknown[]) => uploadDocumentMock(...args),
}));

const prepareQuestionsMock = vi.fn();
vi.mock("../../field-detection/services/apiClient", () => ({
  prepareQuestions: (...args: unknown[]) => prepareQuestionsMock(...args),
}));

vi.mock("../../field-detection/debugMode", () => ({
  isDetectionDebugUiEnabled: () => false,
}));

const BASE_UPLOAD_RESULT = {
  documentId: "doc-1",
  ownershipToken: "doc-token-1",
  status: "analyzed",
  expiresAt: "2026-01-01T00:00:00Z",
};

afterEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
});

async function selectAndSubmitFile() {
  const { default: DocumentUploadForm } =
    await import("../components/DocumentUploadForm");
  render(<DocumentUploadForm currentLocale="en" />);

  const file = new File(["%PDF-1.4"], "test.pdf", { type: "application/pdf" });
  const input = document.querySelector(
    'input[type="file"]',
  ) as HTMLInputElement;
  fireEvent.change(input, { target: { files: [file] } });

  const checkbox = await screen.findByRole("checkbox");
  fireEvent.click(checkbox);

  const submitButton = screen.getByRole("button", {
    name: /upload_and_analyze/i,
  });
  fireEvent.click(submitButton);
}

describe("DocumentUploadForm — automatic upload-to-questions flow (Phase 13)", () => {
  it("navigates straight to the guided session for a high-confidence unknown digital PDF, with no manual review step", async () => {
    uploadDocumentMock.mockResolvedValue({
      ...BASE_UPLOAD_RESULT,
      analysis: {
        pageCount: 1,
        documentType: "digital_pdf",
        hasNativeText: true,
        hasAcroForm: false,
        hasEmbeddedImages: false,
        isProbablyScanned: false,
        matchedTemplate: null,
        nextStep: "dynamic_field_detection",
      },
    });
    prepareQuestionsMock.mockResolvedValue({
      documentId: "doc-1",
      status: "ready",
      sessionId: "session-1",
      ownershipToken: "session-token-1",
      reusedExistingSession: false,
      uncertainty: null,
    });

    await selectAndSubmitFile();

    await waitFor(() =>
      expect(pushMock).toHaveBeenCalledWith("/application/session/session-1"),
    );
    expect(screen.queryByText(/detect_fields/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/start_ocr/i)).not.toBeInTheDocument();
  });

  it("navigates straight through for a known predefined form (fast path)", async () => {
    uploadDocumentMock.mockResolvedValue({
      ...BASE_UPLOAD_RESULT,
      analysis: {
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
      },
    });
    prepareQuestionsMock.mockResolvedValue({
      documentId: "doc-1",
      status: "ready",
      sessionId: "session-2",
      ownershipToken: "session-token-2",
      reusedExistingSession: false,
      uncertainty: null,
    });

    await selectAndSubmitFile();

    await waitFor(() =>
      expect(pushMock).toHaveBeenCalledWith("/application/session/session-2"),
    );
  });

  it("shows a plain-language uncertainty screen (not a raw field editor) and continues on request", async () => {
    uploadDocumentMock.mockResolvedValue({
      ...BASE_UPLOAD_RESULT,
      analysis: {
        pageCount: 1,
        documentType: "digital_pdf",
        hasNativeText: true,
        hasAcroForm: false,
        hasEmbeddedImages: false,
        isProbablyScanned: false,
        matchedTemplate: null,
        nextStep: "dynamic_field_detection",
      },
    });
    prepareQuestionsMock.mockResolvedValue({
      documentId: "doc-1",
      status: "ready",
      sessionId: "session-3",
      ownershipToken: "session-token-3",
      reusedExistingSession: false,
      uncertainty: { hasUncertainFields: true, uncertainFieldCount: 1 },
    });

    await selectAndSubmitFile();

    const continueButton = await screen.findByText(/continue_with_detected/i);
    expect(pushMock).not.toHaveBeenCalled();
    expect(screen.queryByText(/fieldId/i)).not.toBeInTheDocument();

    fireEvent.click(continueButton);
    await waitFor(() =>
      expect(pushMock).toHaveBeenCalledWith("/application/session/session-3"),
    );
  });

  it("shows a safe message (no technical detail) when no usable questions were found", async () => {
    uploadDocumentMock.mockResolvedValue({
      ...BASE_UPLOAD_RESULT,
      analysis: {
        pageCount: 1,
        documentType: "digital_pdf",
        hasNativeText: true,
        hasAcroForm: false,
        hasEmbeddedImages: false,
        isProbablyScanned: false,
        matchedTemplate: null,
        nextStep: "dynamic_field_detection",
      },
    });
    prepareQuestionsMock.mockResolvedValue({
      documentId: "doc-1",
      status: "needs_clarification",
      sessionId: null,
      ownershipToken: null,
      reusedExistingSession: false,
      uncertainty: { hasUncertainFields: true, uncertainFieldCount: 1 },
    });

    await selectAndSubmitFile();

    await screen.findByText(/could_not_process_title/i);
    expect(screen.getByText(/no_usable_questions_body/i)).toBeInTheDocument();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("shows the generic translated fallback (never a raw key) when the backend error has no error code", async () => {
    uploadDocumentMock.mockResolvedValue({
      ...BASE_UPLOAD_RESULT,
      analysis: {
        pageCount: 3,
        documentType: "digital_pdf",
        hasNativeText: true,
        hasAcroForm: false,
        hasEmbeddedImages: false,
        isProbablyScanned: false,
        matchedTemplate: null,
        nextStep: "dynamic_field_detection",
      },
    });
    // Reproduces the reported bug's exact shape: a backend response with
    // no recognized error code, surfaced through ApiError.detail === null.
    prepareQuestionsMock.mockRejectedValue({
      name: "ApiError",
      status: 422,
      message: "Output language 'fr' is not supported by this form version.",
      detail: null,
    });

    await selectAndSubmitFile();

    expect(
      (await screen.findAllByText("error_generic_fallback")).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByText(/error_null/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/documentUpload\./i)).not.toBeInTheDocument();
  });

  it("shows the generic translated fallback for an unrecognized error code", async () => {
    uploadDocumentMock.mockResolvedValue({
      ...BASE_UPLOAD_RESULT,
      analysis: {
        pageCount: 3,
        documentType: "digital_pdf",
        hasNativeText: true,
        hasAcroForm: false,
        hasEmbeddedImages: false,
        isProbablyScanned: false,
        matchedTemplate: null,
        nextStep: "dynamic_field_detection",
      },
    });
    prepareQuestionsMock.mockRejectedValue({
      name: "ApiError",
      status: 500,
      message: "document_processing_failed",
      detail: "document_processing_failed",
    });

    await selectAndSubmitFile();

    expect(
      (await screen.findAllByText("error_generic_fallback")).length,
    ).toBeGreaterThan(0);
    expect(
      screen.queryByText(/error_document_processing_failed/i),
    ).not.toBeInTheDocument();
  });

  it("shows the specific translated message for a known upload error code", async () => {
    uploadDocumentMock.mockRejectedValue({
      name: "ApiError",
      status: 422,
      message: "Only PDF files are supported.",
      detail: "invalid_file_type",
    });

    await selectAndSubmitFile();

    expect(
      (await screen.findAllByText("error_invalid_file_type")).length,
    ).toBeGreaterThan(0);
  });

  it("shows a structured 'failed' orchestration result via the generic fallback, not a raw code", async () => {
    uploadDocumentMock.mockResolvedValue({
      ...BASE_UPLOAD_RESULT,
      analysis: {
        pageCount: 3,
        documentType: "digital_pdf",
        hasNativeText: true,
        hasAcroForm: false,
        hasEmbeddedImages: false,
        isProbablyScanned: false,
        matchedTemplate: null,
        nextStep: "dynamic_field_detection",
      },
    });
    prepareQuestionsMock.mockResolvedValue({
      documentId: "doc-1",
      status: "failed",
      sessionId: null,
      ownershipToken: null,
      reusedExistingSession: false,
      uncertainty: null,
      errorCode: "document_processing_failed",
      stage: "question_generation",
    });

    await selectAndSubmitFile();

    expect(
      (await screen.findAllByText("error_generic_fallback")).length,
    ).toBeGreaterThan(0);
    expect(pushMock).not.toHaveBeenCalled();
  });
});

describe("DocumentUploadForm — slow preparation and stale state", () => {
  const digitalUpload = {
    ...BASE_UPLOAD_RESULT,
    analysis: {
      pageCount: 3,
      documentType: "digital_pdf",
      hasNativeText: true,
      hasAcroForm: false,
      hasEmbeddedImages: false,
      isProbablyScanned: false,
      matchedTemplate: null,
      nextStep: "dynamic_field_detection",
    },
  };

  const readyResult = {
    documentId: "doc-1",
    status: "ready",
    sessionId: "session-1",
    ownershipToken: "session-token-1",
    reusedExistingSession: false,
    uncertainty: null,
    errorCode: null,
    stage: null,
  };

  it("stays on the processing screen while preparation is still running", async () => {
    uploadDocumentMock.mockResolvedValue(digitalUpload);
    // Never settles for the duration of the assertion — the request is still
    // in flight, so no error may be shown.
    prepareQuestionsMock.mockReturnValue(new Promise(() => {}));

    await selectAndSubmitFile();

    await waitFor(() => {
      expect(screen.getByText(/processing/i)).toBeTruthy();
    });
    expect(screen.queryByText("upload_error_title")).toBeNull();
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("recovers from a bare proxy 500 by re-asking, and does not show an error", async () => {
    uploadDocumentMock.mockResolvedValue(digitalUpload);
    // A proxy that abandoned a request the backend was still working on:
    // HTTP 500 with no application error code. The retry hits the idempotent
    // reuse path and returns the finished result.
    const gatewayError: any = new Error("Internal Server Error");
    gatewayError.status = 500;
    prepareQuestionsMock
      .mockRejectedValueOnce(gatewayError)
      .mockResolvedValueOnce({ ...readyResult, reusedExistingSession: true });

    await selectAndSubmitFile();

    await waitFor(
      () => {
        expect(pushMock).toHaveBeenCalledWith("/application/session/session-1");
      },
      { timeout: 10000 },
    );
    expect(prepareQuestionsMock).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("upload_error_title")).toBeNull();
  });

  it("does not retry a real backend error that carries an error code", async () => {
    uploadDocumentMock.mockResolvedValue(digitalUpload);
    const appError: any = new Error("failed");
    appError.status = 500;
    appError.detail = "Field detection failed.";
    appError.errorCode = "field_detection_failed";
    prepareQuestionsMock.mockRejectedValue(appError);

    await selectAndSubmitFile();

    await waitFor(() => {
      expect(screen.getByText("upload_error_title")).toBeTruthy();
    });
    expect(prepareQuestionsMock).toHaveBeenCalledTimes(1);
  });

  it("clears a stale error once a later attempt succeeds", async () => {
    uploadDocumentMock.mockResolvedValue(digitalUpload);
    const appError: any = new Error("failed");
    appError.status = 500;
    appError.errorCode = "field_detection_failed";
    appError.detail = "Field detection failed.";
    prepareQuestionsMock.mockRejectedValueOnce(appError);

    await selectAndSubmitFile();
    await waitFor(() => {
      expect(screen.getByText("upload_error_title")).toBeTruthy();
    });

    // The user retries from the failure screen, which returns the form to its
    // initial state, then submits the same file again — and this time
    // preparation succeeds.
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(screen.queryByText("upload_error_title")).toBeNull();

    prepareQuestionsMock.mockResolvedValueOnce(readyResult);
    const file = new File(["%PDF-1.4"], "retry.pdf", {
      type: "application/pdf",
    });
    const input = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
    await screen.findByText("retry.pdf");
    // Retry keeps the privacy acceptance, so the checkbox must not be
    // toggled again — clicking it would clear consent and block the submit.
    const checkbox = (await screen.findByRole("checkbox")) as HTMLInputElement;
    if (!checkbox.checked) {
      fireEvent.click(checkbox);
    }
    fireEvent.click(
      screen.getByRole("button", { name: /upload_and_analyze/i }),
    );

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/application/session/session-1");
    });
    // The stale error is gone, not merely overlaid by the new result.
    expect(screen.queryByText("upload_error_title")).toBeNull();
    expect(screen.queryByText("error_generic_fallback")).toBeNull();
  });
});
