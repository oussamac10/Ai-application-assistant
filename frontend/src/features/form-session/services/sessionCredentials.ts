/**
 * Safe sessionStorage wrapper for anonymous session tokens.
 * Maps sessionId -> ownershipToken to keep them separate from URLs.
 */

const TOKEN_PREFIX = "session-token:";

export function setSessionToken(sessionId: string, token: string): void {
  if (typeof window !== "undefined") {
    sessionStorage.setItem(`${TOKEN_PREFIX}${sessionId}`, token);
  }
}

export function getSessionToken(sessionId: string): string | null {
  if (typeof window !== "undefined") {
    return sessionStorage.getItem(`${TOKEN_PREFIX}${sessionId}`);
  }
  return null;
}

export function removeSessionToken(sessionId: string): void {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(`${TOKEN_PREFIX}${sessionId}`);
  }
}

export function clearAllTokens(): void {
  if (typeof window !== "undefined") {
    const keys = [];
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i);
      if (key && key.startsWith(TOKEN_PREFIX)) {
        keys.push(key);
      }
    }
    keys.forEach((k) => sessionStorage.removeItem(k));
  }
}
