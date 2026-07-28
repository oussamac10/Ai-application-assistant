/**
 * Safely resolves a translated, user-facing error message for the upload /
 * automatic-processing flow.
 *
 * Never renders a raw i18n key (e.g. "documentUpload.error_null") and never
 * shows backend exception text, provider names, or other technical detail.
 * A deterministic allowlist decides whether a code has a specific
 * translation; anything else — including a missing/null/undefined code —
 * falls back to one generic, always-translated message.
 *
 * Backend error codes come from `app/documents/errors.py`,
 * `app/field_detection/errors.py`, `app/ocr/errors.py`, and the Phase 13
 * orchestration's own `error_code` values (see
 * app/field_detection/orchestration.py). Keep this list in sync when a new
 * *specific* (non-generic) translated message is added for a code.
 */
const KNOWN_ERROR_CODES = new Set([
  "invalid_file_type",
  "file_too_large",
  "malformed_pdf",
  "invalid_pdf",
  "document_analysis_failed",
  "encrypted_pdf",
  "password_protected_pdf",
  "too_many_pages",
  "unsupported_pdf_feature",
  "privacy_not_accepted",
]);

// Stable fallback key — always translated in every supported language
// (see messages/{en,de,fr,ar}.json -> documentUpload.error_generic_fallback).
const GENERIC_FALLBACK_KEY = "error_generic_fallback";

/**
 * Pulls a plausible error code out of any of the response/error shapes this
 * app's various API clients can produce: a bare string, `{ detail }`,
 * `{ code }`, `{ error: { code } }`, or `{ message }`. Never throws.
 */
export function extractErrorCode(err: unknown): string | null {
  if (typeof err === "string" && err.trim()) {
    return err;
  }
  if (!err || typeof err !== "object") {
    return null;
  }

  const anyErr = err as Record<string, unknown>;

  if (typeof anyErr.detail === "string" && anyErr.detail.trim()) {
    return anyErr.detail;
  }
  if (typeof anyErr.code === "string" && anyErr.code.trim()) {
    return anyErr.code;
  }
  if (
    anyErr.error &&
    typeof anyErr.error === "object" &&
    typeof (anyErr.error as Record<string, unknown>).code === "string"
  ) {
    const nestedCode = (anyErr.error as Record<string, unknown>).code as string;
    if (nestedCode.trim()) return nestedCode;
  }
  if (typeof anyErr.message === "string" && anyErr.message.trim()) {
    return anyErr.message;
  }

  return null;
}

/**
 * Resolves the translated message to show the user for a failed upload /
 * automatic-processing attempt. `t` is the `documentUpload`-namespaced
 * translation function from `useTranslations("documentUpload")`.
 */
export function resolveUploadErrorMessage(
  t: (key: string) => string,
  err: unknown
): string {
  const code = extractErrorCode(err);
  if (code && KNOWN_ERROR_CODES.has(code)) {
    const translated = t(`error_${code}`);
    if (translated) return translated;
  }
  return t(GENERIC_FALLBACK_KEY);
}
