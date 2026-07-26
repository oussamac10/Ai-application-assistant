import { ApiError } from "../../form-session/services/apiClient";
import { getDocumentToken } from "../../document-upload/services/documentCredentials";
import { OcrResultResponse, OcrResultResponseSchema } from "../types";

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
  return new ApiError(response.status, detail || "OCR request failed.", errorCode);
}

export async function requestOcr(
  documentId: string,
  language: string
): Promise<OcrResultResponse> {
  const response = await fetch(`/api/source-documents/${documentId}/ocr`, {
    method: "POST",
    headers: authHeaders(documentId),
    body: JSON.stringify({ language }),
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const data = await response.json();
  return OcrResultResponseSchema.parse(data);
}

export async function getOcrResult(documentId: string): Promise<OcrResultResponse> {
  const response = await fetch(`/api/source-documents/${documentId}/ocr`, {
    method: "GET",
    headers: authHeaders(documentId),
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  const data = await response.json();
  return OcrResultResponseSchema.parse(data);
}
