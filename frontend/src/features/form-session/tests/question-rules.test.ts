import { describe, it, expect } from "vitest";

import {
  BooleanChild,
  canSkipQuestion,
  requiredChildrenSatisfied,
  requirednessLabelFor,
  resolveRequiredness,
  unsatisfiedRequiredChildren,
} from "../utils/questionRules";

/**
 * Skip visibility and Continue gating, decided from three-state requiredness
 * rather than a boolean.
 *
 * The reported failure: the declaration screen offered "Skip this question"
 * over two mandatory consents. The group itself carries no requiredness — the
 * *children* do — so a check that looked only at the question said "skippable".
 */

const child = (
  key: string,
  requiredness: BooleanChild["requiredness"],
  value: boolean | null = null,
): BooleanChild => ({ key, label: key, requiredness, value });

describe("resolveRequiredness", () => {
  it("uses the three-state value when present", () => {
    expect(resolveRequiredness({ requiredness: "optional", required: true })).toBe(
      "optional",
    );
  });

  it("reads a legacy true as required", () => {
    expect(resolveRequiredness({ required: true })).toBe("required");
  });

  it("reads a legacy false as unknown, not optional", () => {
    // The boolean could never tell "optional" from "nothing was said", so
    // treating false as optional would resurrect the false claim.
    expect(resolveRequiredness({ required: false })).toBe("unknown");
  });

  it("defaults to unknown when nothing is declared", () => {
    expect(resolveRequiredness({})).toBe("unknown");
  });
});

describe("canSkipQuestion", () => {
  it("allows skipping an optional question", () => {
    expect(canSkipQuestion({ requiredness: "optional" })).toBe(true);
  });

  it("allows skipping an unknown question — unknown does not mean required", () => {
    expect(canSkipQuestion({ requiredness: "unknown" })).toBe(true);
  });

  it("refuses to skip a required question", () => {
    expect(canSkipQuestion({ requiredness: "required" })).toBe(false);
  });

  it("refuses to skip a group containing any required child", () => {
    // The reported failure. Skipping the screen would skip every child, so one
    // required child removes the option — whatever the group itself says.
    expect(
      canSkipQuestion({
        requiredness: "unknown",
        children: [
          child("certify", "required"),
          child("processing", "required"),
          child("newsletter", "optional"),
        ],
      }),
    ).toBe(false);
  });

  it("allows skipping a group whose children are all optional or unknown", () => {
    expect(
      canSkipQuestion({
        children: [child("newsletter", "optional"), child("survey", "unknown")],
      }),
    ).toBe(true);
  });

  it("ignores the group's own requiredness when it has children", () => {
    expect(
      canSkipQuestion({
        requiredness: "optional",
        children: [child("certify", "required")],
      }),
    ).toBe(false);
  });
});

describe("requiredChildrenSatisfied", () => {
  it("is false while any required child is unchecked", () => {
    expect(
      requiredChildrenSatisfied([
        child("certify", "required", true),
        child("processing", "required", null),
      ]),
    ).toBe(false);
  });

  it("is true once every required child is checked", () => {
    expect(
      requiredChildrenSatisfied([
        child("certify", "required", true),
        child("processing", "required", true),
        child("newsletter", "optional", null),
      ]),
    ).toBe(true);
  });

  it("never gates on an optional or unknown child", () => {
    // "No" is a complete answer to "would you like to receive news?".
    expect(
      requiredChildrenSatisfied([
        child("newsletter", "optional", false),
        child("survey", "unknown", null),
      ]),
    ).toBe(true);
  });

  it("treats an explicit false as unsatisfied for a required child", () => {
    expect(requiredChildrenSatisfied([child("certify", "required", false)])).toBe(
      false,
    );
  });
});

describe("unsatisfiedRequiredChildren", () => {
  it("names only the required children still unchecked", () => {
    const result = unsatisfiedRequiredChildren([
      child("certify", "required", true),
      child("processing", "required", null),
      child("newsletter", "optional", null),
    ]);

    expect(result.map((c) => c.key)).toEqual(["processing"]);
  });
});

describe("requirednessLabelFor", () => {
  it("renders no label for unknown", () => {
    expect(requirednessLabelFor({ requiredness: "unknown" })).toBeNull();
  });

  it("renders a label for a real finding", () => {
    expect(requirednessLabelFor({ requiredness: "required" })).toBe("required");
    expect(requirednessLabelFor({ requiredness: "optional" })).toBe("optional");
  });

  it("renders no label when only a legacy false is available", () => {
    expect(requirednessLabelFor({ required: false })).toBeNull();
  });
});
