/**
 * Turning an export failure into something a person can act on.
 *
 * The screen previously showed `error.detail` — whatever string the backend
 * happened to send — for anything that was not a 401 or a 422. That is both
 * unhelpful ("PDF rendering failed: …") and unsafe: a detail field is the wrong
 * place to trust, because one careless `raise` upstream turns it into a library
 * message or a file path on a user's screen.
 *
 * So nothing from the response is ever rendered. A deterministic allowlist maps
 * known codes to translated messages, and everything else — including a missing
 * or unrecognised code — falls back to one generic sentence.
 *
 * Signature failures get their own treatment because the useful action differs:
 * a signature that cannot be placed or is no longer valid is fixed by going back
 * and signing again, which is worth offering rather than leaving someone to
 * retry an export that will fail the same way.
 */

/** Codes with a specific translated message. Keep in step with
 * `app/pdf/signature_render.py` and the export service's error codes. */
const KNOWN_EXPORT_ERRORS = new Set([
  "export_forbidden",
  "signature_mapping_missing",
  "signature_invalid",
  "signature_too_large",
  "signature_export_failed",
  "template_mapping_invalid",
]);

/** Failures a user can clear by returning to the signature question.
 *
 * `signature_mapping_missing` and `template_mapping_invalid` are deliberately
 * absent: those are faults in the template, and re-signing would waste the
 * user's time on something they cannot fix. */
const RESIGNABLE_ERRORS = new Set([
  "signature_invalid",
  "signature_too_large",
  "signature_export_failed",
]);

const GENERIC_FALLBACK_KEY = "exportFailed";

/** Pulls a code out of the shapes the export API can produce. Never throws. */
export function extractExportErrorCode(error: unknown): string | null {
  if (!error || typeof error !== "object") return null;
  const anyError = error as Record<string, unknown>;

  for (const key of ["errorCode", "error_code", "code", "detail"]) {
    const value = anyError[key];
    if (typeof value === "string" && KNOWN_EXPORT_ERRORS.has(value)) {
      return value;
    }
  }
  return null;
}

export interface ExportErrorPresentation {
  message: string;
  /** Whether returning to the signature question would help. */
  canResign: boolean;
  /** Whether retrying the same export is worth offering. */
  canRetry: boolean;
}

/**
 * Resolves what to show for a failed export.
 *
 * `t` is the `complete`-namespaced translation function.
 */
export function resolveExportError(
  t: (key: string) => string,
  error: unknown,
): ExportErrorPresentation {
  const code = extractExportErrorCode(error);
  if (!code) {
    return { message: t(GENERIC_FALLBACK_KEY), canResign: false, canRetry: true };
  }
  return {
    message: t(`error_${code}`),
    canResign: RESIGNABLE_ERRORS.has(code),
    // A permission failure will not resolve by trying again, and a broken
    // template mapping will not either — offering a retry button there invites
    // someone to press it repeatedly for nothing.
    canRetry: code !== "export_forbidden" && code !== "template_mapping_invalid",
  };
}
