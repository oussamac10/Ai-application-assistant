import { describe, expect, it } from "vitest";
import { cn } from "./utils";

describe("cn utility", () => {
  it("joins simple class strings", () => {
    expect(cn("px-4", "py-2", "text-sm")).toBe("px-4 py-2 text-sm");
  });

  it("filters out falsy values like false, null, undefined, and empty string", () => {
    expect(cn("base-class", false, null, undefined, "", "extra-class")).toBe(
      "base-class extra-class",
    );
  });

  it("evaluates object conditionals correctly", () => {
    expect(
      cn("btn", {
        "btn-primary": true,
        "btn-disabled": false,
        "shadow-sm": 1,
        "hidden": 0,
      }),
    ).toBe("btn btn-primary shadow-sm");
  });

  it("flattens nested arrays of classes and conditionals", () => {
    expect(
      cn(
        "first",
        ["second", ["nested", { active: true, inactive: false }]],
        undefined,
        "last",
      ),
    ).toBe("first second nested active last");
  });

  it("returns empty string when called with no arguments or only falsy values", () => {
    expect(cn()).toBe("");
    expect(cn(null, undefined, false)).toBe("");
  });
});
