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
    const amtNum = Number(value.amount);
    const amountStr = !Number.isNaN(amtNum) ? String(amtNum) : String(value.amount);
    const period =
      typeof value.period === "string" &&
      value.period.trim().length > 0 &&
      value.period.trim().toLowerCase() !== "once"
        ? value.period.trim()
        : null;
    return [amountStr, value.currency, period]
      .filter((part) => (typeof part === "string" && part.length > 0) || typeof part === "number")
      .join(" ");
  },
  signature: (value) =>
    value &&
    typeof value === "object" &&
    Array.isArray(value.strokes) &&
    value.strokes.length > 0
      ? "Digital signature captured"
      : null,
};

export function formatOriginalAnswer(
  rawAnswer: string | null | undefined,
  fieldType?: string | null,
  options?: Array<{ value: string; label: string }> | null
): string {
  if (typeof rawAnswer !== "string" || rawAnswer.trim().length === 0) {
    return "";
  }
  const trimmed = rawAnswer.trim();

  if (
    fieldType === "multiple_choice" ||
    (trimmed.startsWith("[") && trimmed.endsWith("]"))
  ) {
    try {
      const parsed = JSON.parse(trimmed);
      if (Array.isArray(parsed)) {
        return parsed
          .map((item) => {
            const strItem = String(item);
            return options?.find((opt) => opt.value === strItem)?.label ?? strItem;
          })
          .join(", ");
      }
    } catch {
      // Not valid JSON; fall through to raw display
    }
  }

  if (fieldType === "single_choice" && options && options.length > 0) {
    return options.find((opt) => opt.value === trimmed)?.label ?? rawAnswer;
  }

  if (fieldType === "boolean" || (!fieldType && (trimmed === "true" || trimmed === "false"))) {
    const low = trimmed.toLowerCase();
    if (low === "true" || low === "1" || low === "yes") return "Yes";
    if (low === "false" || low === "0" || low === "no") return "No";
  }

  return rawAnswer;
}

export function formatProposedValue(
  normalizedValue: unknown,
  outputValue: string | null | undefined,
  fieldType?: string | null
): string {
  if (fieldType === "boolean" || typeof normalizedValue === "boolean") {
    if (typeof outputValue === "string" && outputValue.trim().length > 0) {
      const low = outputValue.trim().toLowerCase();
      if (low === "true") return "Yes";
      if (low === "false") return "No";
      return outputValue;
    }
    if (normalizedValue === true) return "Yes";
    if (normalizedValue === false) return "No";
  }

  if (fieldType === "money" && normalizedValue && typeof normalizedValue === "object") {
    const formatted = STRUCTURED_FIELD_FORMATTERS.money(normalizedValue);
    if (formatted) return formatted;
  }

  if (typeof outputValue === "string" && outputValue.trim().length > 0) {
    if (fieldType === "money") {
      return outputValue
        .replace(/\b(\d+)\.0\b/g, "$1")
        .replace(/\s+once$/i, "")
        .trim();
    }
    return outputValue;
  }

  if (normalizedValue === null || normalizedValue === undefined) {
    return "";
  }

  if (
    typeof normalizedValue === "string" ||
    typeof normalizedValue === "number"
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
