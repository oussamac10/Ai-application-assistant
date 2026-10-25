const LEADING_ASTERISK_RE = /^\s*[*∗]+\s*(?=\S)/;
const TRAILING_MARKER_RE = /\s*(?:\(\s*[*∗]\s*\)|[*∗]+)\s*[:：]?\s*$/;
const TRAILING_COLON_RE = /\s*[:：]\s*$/;

/**
 * Normalizes a field label for display so requiredness markers (`*`, `(*)`),
 * trailing colons, and unpaired OCR-corrupted trailing quotes (`Last name "`)
 * do not duplicate or clutter the UI's own requiredness indicator.
 */
export function formatFieldLabel(label: string): string {
  if (!label) return "";
  let cleaned = label
    .replace(LEADING_ASTERISK_RE, "")
    .replace(TRAILING_MARKER_RE, "")
    .replace(TRAILING_COLON_RE, "")
    .trim();

  if ((cleaned.match(/"/g)?.length ?? 0) === 1 && /\s"\s*$/.test(cleaned)) {
    cleaned = cleaned.replace(/\s+"\s*$/, "").trim();
  }

  return cleaned || label.trim();
}
