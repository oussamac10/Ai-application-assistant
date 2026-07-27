/**
 * Reads the CSRF double-submit cookie set by the backend (readable by our
 * own frontend JS since it is not HttpOnly) so it can be echoed back as the
 * X-CSRF-Token header on cookie-authenticated mutations.
 */
export function getCsrfToken(): string | null {
  if (typeof document === "undefined") {
    return null;
  }
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}
