/**
 * Safely formats an answer's proposed (normalized/output) value for
 * display on the confirmation screen.
 *
 * Never renders a raw object/array as JSON — a malformed or unexpected AI
 * response (e.g. the backend's Ollama-provider bug where the model's
 * reasoning ended up nested inside `normalizedValue` instead of a plain
 * value) must degrade to a safe, empty/blank display, never
 * `JSON.stringify`'d object text shown to the user.
 */

// Field types documented (backend/app/ai/prompts/extract_value_v1.txt) to
// legitimately produce a structured normalizedValue object. Only these get
// a best-effort friendly summary; any other object shape is unexpected and
// is never rendered.
const STRUCTURED_FIELD_FORMATTERS: Record<string, (value: any) => string | null> = {
  person_name: (value) =>
    value && typeof value === "object" && typeof value.fullName === "string"
      ? value.fullName
      : null,
  money: (value) => {
    if (!value || typeof value !== "object" || value.amount == null) return null;
    return [String(value.amount), value.currency, value.period]
      .filter((part) => typeof part === "string" || typeof part === "number")
      .join(" ");
  },
};

export function formatProposedValue(
  normalizedValue: unknown,
  outputValue: string | null | undefined,
  fieldType?: string
): string {
  if (typeof outputValue === "string" && outputValue.trim().length > 0) {
    return outputValue;
  }

  if (normalizedValue === null || normalizedValue === undefined) {
    return "";
  }

  if (
    typeof normalizedValue === "string" ||
    typeof normalizedValue === "number" ||
    typeof normalizedValue === "boolean"
  ) {
    return String(normalizedValue);
  }

  if (Array.isArray(normalizedValue)) {
    return normalizedValue.map((item) => String(item)).join(", ");
  }

  // Only reached for an object value. Never JSON.stringify it — either a
  // documented structured field type produces a friendly summary, or the
  // display is safely left blank.
  if (fieldType && STRUCTURED_FIELD_FORMATTERS[fieldType]) {
    const formatted = STRUCTURED_FIELD_FORMATTERS[fieldType](normalizedValue);
    if (formatted) return formatted;
  }

  return "";
}
