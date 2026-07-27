import { z } from "zod";
import { getSessionToken } from "./sessionCredentials";

// --- API Response Schemas ---

export const PublishedFormSchema = z.object({
  id: z.string(),
  templateKey: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  versionNumber: z.number(),
  sourceLanguage: z.string(),
  supportedOutputLanguages: z.array(z.string()),
});

export type PublishedForm = z.infer<typeof PublishedFormSchema>;

export const SessionResponseSchema = z.object({
  id: z.string().optional(),
  sessionId: z.string().optional(),
  publicId: z.string(),
  status: z.string(),
  ownershipToken: z.string().optional(),
  userLanguage: z.string(),
  outputLanguage: z.string(),
  expiresAt: z.string(),
  createdAt: z.string().optional(),
  formOrigin: z.string().optional(),
  exportSupported: z.boolean().optional(),
});

export type FormSession = z.infer<typeof SessionResponseSchema>;

export const FieldOptionSchema = z.object({
  value: z.string(),
  label: z.string(),
});

export const ProgressInfoSchema = z.object({
  confirmedRequiredFields: z.number(),
  totalRequiredFields: z.number(),
  percentage: z.number(),
});

export const CurrentFieldResponseSchema = z.object({
  id: z.string(),
  key: z.string(),
  fieldType: z.string(),
  required: z.boolean(),
  position: z.number(),
  label: z.string(),
  helpText: z.string().nullable().optional(),
  placeholder: z.string().nullable().optional(),
  options: z.array(FieldOptionSchema).nullable().optional(),
  currentAnswerStatus: z.string().nullable().optional(),
  progress: ProgressInfoSchema.nullable().optional(),
  fieldId: z.string(),
  fieldKey: z.string(),
});

export type CurrentField = z.infer<typeof CurrentFieldResponseSchema>;

export const ClarificationResponseSchema = z.object({
  missing: z.array(z.string()),
  questionKey: z.string(),
});

export const AnswerResponseSchema = z.object({
  id: z.string(),
  fieldId: z.string().optional(),
  originalAnswer: z.string(),
  normalizedValue: z.any().nullable().optional(),
  outputValue: z.string().nullable().optional(),
  status: z.string(), // e.g. answered, draft, needs_clarification, awaiting_confirmation, confirmed
  validationStatus: z.string().optional(),
  clarification: ClarificationResponseSchema.nullable().optional(),
});

export type AnswerResponse = z.infer<typeof AnswerResponseSchema>;

export const SummaryFieldSchema = z.object({
  fieldId: z.string(),
  fieldKey: z.string(),
  label: z.string(),
  required: z.boolean(),
  originalAnswer: z.string().nullable(),
  outputValue: z.string().nullable(),
  status: z.string(),
});

export const SummaryResponseSchema = z.object({
  fields: z.array(SummaryFieldSchema),
});

export type Summary = z.infer<typeof SummaryResponseSchema>;

// --- API Error Class ---

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail: string | null = null
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// --- Fetch client wrapper ---

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  sessionId?: string,
  schema?: z.ZodSchema<T>
): Promise<T> {
  const baseUrl = "/api";
  const headers = new Headers(options.headers || {});
  
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (sessionId) {
    const token = getSessionToken(sessionId);
    if (token) {
      headers.set("X-Session-Token", token);
    }
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = null;
    try {
      const data = await response.json();
      detail = data.detail || null;
    } catch {
      // ignore
    }

    if (response.status === 401) {
      throw new ApiError(401, "unauthorized", detail);
    } else if (response.status === 409) {
      throw new ApiError(409, "conflict", detail);
    } else if (response.status === 422) {
      throw new ApiError(422, "validation", detail);
    } else if (response.status >= 500) {
      throw new ApiError(503, "unavailable", detail);
    }
    throw new ApiError(response.status, "unknown", detail);
  }

  const data = await response.json();
  if (schema) {
    return schema.parse(data);
  }
  return data as T;
}

// --- API Client Endpoints ---

export async function getPublishedForms(): Promise<PublishedForm[]> {
  return apiRequest("/published-forms", { method: "GET" }, undefined, z.array(PublishedFormSchema));
}

export async function createSession(
  versionId: string,
  userLanguage: string,
  outputLanguage: string
): Promise<FormSession> {
  return apiRequest(
    `/form-versions/${versionId}/sessions`,
    {
      method: "POST",
      body: JSON.stringify({ userLanguage, outputLanguage }),
    },
    undefined,
    SessionResponseSchema
  );
}

export async function getSession(sessionId: string): Promise<FormSession> {
  return apiRequest(`/form-sessions/${sessionId}`, { method: "GET" }, sessionId, SessionResponseSchema);
}

export async function startSession(sessionId: string): Promise<FormSession> {
  return apiRequest(`/form-sessions/${sessionId}/start`, { method: "POST" }, sessionId, SessionResponseSchema);
}

export async function cancelSession(sessionId: string): Promise<FormSession> {
  return apiRequest(`/form-sessions/${sessionId}/cancel`, { method: "POST" }, sessionId, SessionResponseSchema);
}

export async function getCurrentField(sessionId: string): Promise<CurrentField> {
  return apiRequest(`/form-sessions/${sessionId}/current-field`, { method: "GET" }, sessionId, CurrentFieldResponseSchema);
}

export async function submitAnswer(
  sessionId: string,
  fieldId: string,
  originalAnswer: string
): Promise<AnswerResponse> {
  return apiRequest(
    `/form-sessions/${sessionId}/answers`,
    {
      method: "POST",
      body: JSON.stringify({ fieldId, originalAnswer }),
    },
    sessionId,
    AnswerResponseSchema
  );
}

export async function submitClarification(
  sessionId: string,
  answerId: string,
  values: Record<string, any>
): Promise<AnswerResponse> {
  return apiRequest(
    `/form-sessions/${sessionId}/answers/${answerId}/clarify`,
    {
      method: "POST",
      body: JSON.stringify({ values }),
    },
    sessionId,
    AnswerResponseSchema
  );
}

export async function confirmAnswer(sessionId: string, answerId: string): Promise<AnswerResponse> {
  return apiRequest(
    `/form-sessions/${sessionId}/answers/${answerId}/confirm`,
    { method: "POST" },
    sessionId,
    AnswerResponseSchema
  );
}

export async function changeAnswer(
  sessionId: string,
  fieldId: string,
  originalAnswer: string
): Promise<AnswerResponse> {
  return apiRequest(
    `/form-sessions/${sessionId}/fields/${fieldId}/answer`,
    {
      method: "PUT",
      body: JSON.stringify({ originalAnswer }),
    },
    sessionId,
    AnswerResponseSchema
  );
}

export async function previousField(sessionId: string): Promise<CurrentField> {
  return apiRequest(
    `/form-sessions/${sessionId}/previous-field`,
    { method: "POST" },
    sessionId,
    CurrentFieldResponseSchema
  );
}

export async function getSummary(sessionId: string): Promise<Summary> {
  return apiRequest(`/form-sessions/${sessionId}/summary`, { method: "GET" }, sessionId, SummaryResponseSchema);
}

export async function confirmSummary(sessionId: string): Promise<{ status: string }> {
  return apiRequest(
    `/form-sessions/${sessionId}/confirm-summary`,
    { method: "POST" },
    sessionId,
    z.object({ status: z.string() })
  );
}

export const ExportResponseSchema = z.object({
  exportId: z.string(),
  status: z.string(),
  fileName: z.string(),
  contentType: z.string(),
  fileSize: z.number().nullable().optional(),
  expiresAt: z.string(),
  downloadUrl: z.string(),
});

export type ExportResponse = z.infer<typeof ExportResponseSchema>;

/** Thrown when the session token is missing from sessionStorage (e.g. tab was closed). */
export class TokenMissingError extends Error {
  constructor() {
    super("Session token not found. Please start a new session.");
    this.name = "TokenMissingError";
  }
}

export async function createExport(sessionId: string): Promise<ExportResponse> {
  // No token requirement here: a claimed session has no anonymous
  // ownership token at all and authorizes via the auth cookie instead.
  // apiRequest already omits the X-Session-Token header when none is
  // stored, so the cookie-only path works unmodified.
  return apiRequest(
    `/form-sessions/${sessionId}/exports`,
    { method: "POST" },
    sessionId,
    ExportResponseSchema
  );
}

export async function downloadExportBlob(sessionId: string, downloadUrl: string): Promise<Blob> {
  const token = getSessionToken(sessionId);
  const headers = new Headers();
  if (token) {
    headers.set("X-Session-Token", token);
  }
  const response = await fetch(downloadUrl, {
    method: "GET",
    headers,
  });
  if (!response.ok) {
    let detail = null;
    try {
      const data = await response.json();
      detail = data.detail || null;
    } catch {
      // ignore
    }
    throw new ApiError(response.status, "Download failed", detail);
  }
  return response.blob();
}

