/**
 * Safe sessionStorage wrapper for anonymous document ownership tokens.
 * Maps documentId -> ownershipToken to keep them separate from URLs.
 */

const DOC_TOKEN_PREFIX = "document-token:";

export function setDocumentToken(documentId: string, token: string): void {
  if (typeof window !== "undefined") {
    sessionStorage.setItem(`${DOC_TOKEN_PREFIX}${documentId}`, token);
  }
}

export function getDocumentToken(documentId: string): string | null {
  if (typeof window !== "undefined") {
    return sessionStorage.getItem(`${DOC_TOKEN_PREFIX}${documentId}`);
  }
  return null;
}

export function removeDocumentToken(documentId: string): void {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(`${DOC_TOKEN_PREFIX}${documentId}`);
  }
}
