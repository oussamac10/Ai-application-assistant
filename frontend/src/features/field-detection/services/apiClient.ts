import { ApiError } from "../../form-session/services/apiClient";
import { getDocumentToken } from "../../document-upload/services/documentCredentials";
import {
  DetectedField,
  FieldDetectionResultResponse,
  FieldDetectionResultResponseSchema,
  SessionCreateResponse,
  SessionCreateResponseSchema,
} from "../types";

function authHeaders(documentId: string): Record<string, string> {
  const token = getDocumentToken(documentId);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
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
  return new ApiError(response.status, detail || "Field detection request failed.", errorCode);
}

export async function requestFieldDetection(
  documentId: string
): Promise<FieldDetectionResultResponse> {
  const response = await fetch(`/api/source-documents/${documentId}/field-detection`, {
    method: "POST",
    headers: authHeaders(documentId),
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const data = await response.json();
  return FieldDetectionResultResponseSchema.parse(data);
}

export async function getFieldDetectionResult(
  documentId: string
): Promise<FieldDetectionResultResponse> {
  const response = await fetch(`/api/source-documents/${documentId}/field-detection`, {
    method: "GET",
    headers: authHeaders(documentId),
  });

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
  updates: DetectedFieldUpdate
): Promise<DetectedField> {
  const response = await fetch(
    `/api/source-documents/${documentId}/field-detection/fields/${fieldId}`,
    {
      method: "PATCH",
      headers: authHeaders(documentId),
      body: JSON.stringify(updates),
    }
  );

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const data = await response.json();
  return data as DetectedField;
}

export async function rejectDetectedField(
  documentId: string,
  fieldId: string
): Promise<DetectedField> {
  const response = await fetch(
    `/api/source-documents/${documentId}/field-detection/fields/${fieldId}`,
    {
      method: "DELETE",
      headers: authHeaders(documentId),
    }
  );

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const data = await response.json();
  return data as DetectedField;
}

export async function createSessionFromFieldDetection(
  documentId: string,
  language: string,
  outputLanguage: string
): Promise<SessionCreateResponse> {
  const response = await fetch(`/api/source-documents/${documentId}/field-detection/session`, {
    method: "POST",
    headers: authHeaders(documentId),
    body: JSON.stringify({ language, outputLanguage }),
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const data = await response.json();
  return SessionCreateResponseSchema.parse(data);
}
