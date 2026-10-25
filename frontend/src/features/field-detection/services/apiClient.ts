import { ApiError } from "../../form-session/services/apiClient";
import { getDocumentToken } from "../../document-upload/services/documentCredentials";
import {
  DetectedField,
  FieldDetectionResultResponse,
  FieldDetectionResultResponseSchema,
  JobStatusResponse,
  JobStatusResponseSchema,
  PrepareQuestionsAcceptedSchema,
  PrepareQuestionsResponse,
  PrepareQuestionsResponseSchema,
  SessionCreateResponse,
  SessionCreateResponseSchema,
} from "../types";

function authHeaders(documentId: string): Record<string, string> {
  const token = getDocumentToken(documentId);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["X-Document-Token"] = token;
  }
  return headers;
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  let detail: string | null = null;
  let errorCode: string | null = null;
  try {
    const errorData = await response.json();
    detail = errorData.detail;
    errorCode = errorData.error_code;
  } catch {
    // ignore
  }
  return new ApiError(
    response.status,
    detail || "Field detection request failed.",
    errorCode,
  );
}

export async function requestFieldDetection(
  documentId: string,
): Promise<FieldDetectionResultResponse> {
  const response = await fetch(
    `/api/source-documents/${documentId}/field-detection`,
    {
      method: "POST",
      headers: authHeaders(documentId),
    },
  );

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const data = await response.json();
  return FieldDetectionResultResponseSchema.parse(data);
}

export async function getFieldDetectionResult(
  documentId: string,
): Promise<FieldDetectionResultResponse> {
  const response = await fetch(
    `/api/source-documents/${documentId}/field-detection`,
    {
      method: "GET",
      headers: authHeaders(documentId),
    },
  );

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const data = await response.json();
  return FieldDetectionResultResponseSchema.parse(data);
}

export interface DetectedFieldUpdate {
  label?: string;
  normalizedName?: string;
  fieldType?: string;
  required?: boolean;
  reviewStatus?: string;
}

export async function updateDetectedField(
  documentId: string,
  fieldId: string,
  updates: DetectedFieldUpdate,
): Promise<DetectedField> {
  const response = await fetch(
    `/api/source-documents/${documentId}/field-detection/fields/${fieldId}`,
    {
      method: "PATCH",
      headers: authHeaders(documentId),
      body: JSON.stringify(updates),
    },
  );

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const data = await response.json();
  return data as DetectedField;
}

export async function rejectDetectedField(
  documentId: string,
  fieldId: string,
): Promise<DetectedField> {
  const response = await fetch(
    `/api/source-documents/${documentId}/field-detection/fields/${fieldId}`,
    {
      method: "DELETE",
      headers: authHeaders(documentId),
    },
  );

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const data = await response.json();
  return data as DetectedField;
}

/** Phase 13 — the single call the normal-user upload flow makes: analyze ->
 * OCR (if needed) -> detect fields -> auto-confirm what's safe -> generate
 * questions -> create/reuse the guided session. Idempotent: safe to call
 * again (e.g. on resume) without reprocessing or duplicating the session. */
/** In-flight prepare-questions requests, keyed by document + languages.
 *
 * Preparation is slow (Azure/OCR plus AI translation, tens of seconds), and
 * the backend is idempotent, so a duplicate request is never *wrong* — but it
 * is wasteful and it lets two responses race to set component state. React
 * Strict Mode's double-invoked effects and an impatient second click both
 * produce that duplicate, so concurrent callers share one request and one
 * result instead. Cleared when the request settles, which means a genuine
 * retry after a failure still reaches the backend. */
const inFlightPreparations = new Map<
  string,
  Promise<PrepareQuestionsResponse>
>();

export interface PrepareQuestionsOptions {
  pollIntervalMs?: number;
  maxPollAttempts?: number;
}

export async function getProcessingJobStatus(
  documentId: string,
  jobId: string,
): Promise<JobStatusResponse> {
  const response = await fetch(`/api/jobs/${jobId}`, {
    method: "GET",
    headers: authHeaders(documentId),
  });
  if (!response.ok) {
    throw await parseErrorResponse(response);
  }
  const data = await response.json();
  return JobStatusResponseSchema.parse(data);
}

export async function prepareQuestions(
  documentId: string,
  language: string,
  /** Omitted by the upload flow: the completed form is written in the
   * language the *form* is in, which the backend detects from the document.
   * Only callers that genuinely offer a choice (the manual template flow)
   * pass one. */
  outputLanguage?: string,
  options?: PrepareQuestionsOptions,
): Promise<PrepareQuestionsResponse> {
  const key = `${documentId}:${language}:${outputLanguage ?? "auto"}`;
  const existing = inFlightPreparations.get(key);
  if (existing) {
    return existing;
  }

  const pollIntervalMs = options?.pollIntervalMs ?? 1200;
  const maxPollAttempts = options?.maxPollAttempts ?? 150;

  const request: Promise<PrepareQuestionsResponse> = (
    async (): Promise<PrepareQuestionsResponse> => {
    const response = await fetch(
      `/api/source-documents/${documentId}/prepare-questions`,
      {
        method: "POST",
        headers: authHeaders(documentId),
        body: JSON.stringify({ language, outputLanguage }),
      },
    );

    if (!response.ok) {
      throw await parseErrorResponse(response);
    }

    const data = await response.json();
    if (
      response.status === 202 ||
      data?.status === "queued" ||
      data?.status === "running"
    ) {
      const accepted = PrepareQuestionsAcceptedSchema.parse(data);
      for (let attempt = 0; attempt < maxPollAttempts; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
        const jobStatus = await getProcessingJobStatus(
          documentId,
          accepted.jobId,
        );
        if (jobStatus.status === "completed" && jobStatus.result) {
          return jobStatus.result;
        }
        if (jobStatus.status === "failed") {
          if (jobStatus.result) {
            return jobStatus.result;
          }
          return {
            documentId,
            status: "failed",
            sessionId: null,
            ownershipToken: null,
            reusedExistingSession: false,
            uncertainty: null,
            errorCode: jobStatus.errorCode ?? "document_processing_failed",
            stage: jobStatus.stage ?? null,
          };
        }
      }
      throw new ApiError(
        504,
        "Document preparation timed out.",
        "document_processing_failed",
      );
    }

    return PrepareQuestionsResponseSchema.parse(data);
    }
  )();

  inFlightPreparations.set(key, request);
  try {
    return await request;
  } finally {
    inFlightPreparations.delete(key);
  }
}

export async function createSessionFromFieldDetection(
  documentId: string,
  language: string,
  outputLanguage: string,
): Promise<SessionCreateResponse> {
  const response = await fetch(
    `/api/source-documents/${documentId}/field-detection/session`,
    {
      method: "POST",
      headers: authHeaders(documentId),
      body: JSON.stringify({ language, outputLanguage }),
    },
  );

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const data = await response.json();
  return SessionCreateResponseSchema.parse(data);
}
