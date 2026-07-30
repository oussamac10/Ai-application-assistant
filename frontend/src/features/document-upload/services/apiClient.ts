import { ApiError } from "../../form-session/services/apiClient";
import { getDocumentToken } from "./documentCredentials";
import {
  DocumentUploadResponse,
  DocumentUploadResponseSchema,
  DocumentRetrieveResponse,
  DocumentRetrieveResponseSchema,
  SessionCreateResponse,
  SessionCreateResponseSchema,
} from "../types";

export function uploadDocument(
  file: File,
  language: string,
  /** Optional since Phase 15: the completed form's language is the *form's*
   * own language, detected from the document rather than chosen at upload. */
  outputLanguage: string | undefined,
  privacyAccepted: boolean,
  onProgress?: (percent: number) => void,
): Promise<DocumentUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/source-documents");

    if (onProgress) {
      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      });
    }

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          resolve(DocumentUploadResponseSchema.parse(data));
        } catch (e) {
          reject(new Error("Invalid response format."));
        }
      } else {
        let detail = null;
        let errorCode = null;
        try {
          const errorData = JSON.parse(xhr.responseText);
          detail = errorData.detail;
          errorCode = errorData.error_code;
        } catch {
          // ignore
        }
        reject(new ApiError(xhr.status, detail || "Upload failed", errorCode));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error("Network error during upload."));
    });

    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);
    if (outputLanguage) {
      formData.append("outputLanguage", outputLanguage);
    }
    formData.append("privacyAccepted", String(privacyAccepted));

    xhr.send(formData);
  });
}

export async function getDocument(
  documentId: string,
): Promise<DocumentRetrieveResponse> {
  const token = getDocumentToken(documentId);
  const headers: Record<string, string> = {};
  if (token) {
    headers["X-Document-Token"] = token;
  }

  const response = await fetch(`/api/source-documents/${documentId}`, {
    method: "GET",
    headers,
  });

  if (!response.ok) {
    let detail = null;
    try {
      const errorData = await response.json();
      detail = errorData.detail;
    } catch {
      // ignore
    }
    throw new ApiError(
      response.status,
      "Failed to retrieve document details.",
      detail,
    );
  }

  const data = await response.json();
  return DocumentRetrieveResponseSchema.parse(data);
}

export async function createSessionFromDocument(
  documentId: string,
  language: string,
  outputLanguage: string,
): Promise<SessionCreateResponse> {
  const token = getDocumentToken(documentId);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["X-Document-Token"] = token;
  }

  const response = await fetch(`/api/source-documents/${documentId}/session`, {
    method: "POST",
    headers,
    body: JSON.stringify({ language, outputLanguage }),
  });

  if (!response.ok) {
    let detail = null;
    try {
      const errorData = await response.json();
      detail = errorData.detail;
    } catch {
      // ignore
    }
    throw new ApiError(
      response.status,
      "Failed to create session from document.",
      detail,
    );
  }

  const data = await response.json();
  return SessionCreateResponseSchema.parse(data);
}
