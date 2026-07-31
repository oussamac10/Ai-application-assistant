/**
 * Whether a question can be skipped, and whether it is ready to continue.
 *
 * Both were previously decided inline from `required: boolean`, which cannot
 * express "the document said nothing" and cannot express a group whose
 * *children* carry their own requiredness. The visible consequences were a
 * declaration screen offering "Skip this question" over two mandatory consents,
 * and unmarked questions labelled "Optional".
 */

export type Requiredness = "required" | "optional" | "unknown";

export interface BooleanChild {
  key: string;
  label: string;
  requiredness: Requiredness;
  value?: boolean | null;
}

export interface SkippableQuestion {
  requiredness?: string;
  /** Legacy boolean. Compatibility only — never the source of truth. */
  required?: boolean;
  fieldType?: string;
  children?: BooleanChild[];
}

/** The three-state value, reading the legacy boolean only as a last resort.
 *
 * A backend that predates the column omits `requiredness`. `required === true`
 * is still a positive finding, but `false` is *not* evidence of "optional" —
 * the boolean could not tell "optional" from "nothing was said" — so it reads
 * as `unknown`. That is the safe direction: it neither blocks the user nor
 * claims the document said something it did not. */
export function resolveRequiredness(question: SkippableQuestion): Requiredness {
  const declared = question.requiredness;
  if (declared === "required" || declared === "optional" || declared === "unknown") {
    return declared;
  }
  return question.required ? "required" : "unknown";
}

/**
 * Whether the whole question may be skipped.
 *
 * For a compound group the answer comes from the *children*: skipping the
 * screen would skip every one of them, so a single required child removes the
 * option. The group's own requiredness is irrelevant — a declaration block
 * carries none, which is exactly why the global Skip appeared over two
 * mandatory consents.
 */
export function canSkipQuestion(question: SkippableQuestion): boolean {
  const children = question.children;
  if (children && children.length > 0) {
    return !children.some((child) => child.requiredness === "required");
  }
  return resolveRequiredness(question) !== "required";
}

/**
 * Whether a compound group's required children are all satisfied.
 *
 * Only `required` children gate Continue. An optional or unmarked child left
 * unchecked is a complete answer — "no" is an answer to "would you like to
 * receive news?".
 */
export function requiredChildrenSatisfied(children: BooleanChild[]): boolean {
  return children
    .filter((child) => child.requiredness === "required")
    .every((child) => child.value === true);
}

/** The required children still unchecked, for field-level messaging. */
export function unsatisfiedRequiredChildren(
  children: BooleanChild[],
): BooleanChild[] {
  return children.filter(
    (child) => child.requiredness === "required" && child.value !== true,
  );
}

/**
 * Whether a requiredness label should be rendered at all.
 *
 * `unknown` renders nothing: saying "Optional" there claims the document made
 * a statement it never made.
 */
export function requirednessLabelFor(
  question: SkippableQuestion,
): "required" | "optional" | null {
  const state = resolveRequiredness(question);
  return state === "unknown" ? null : state;
}
