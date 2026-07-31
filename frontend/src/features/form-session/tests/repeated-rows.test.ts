import { describe, it, expect } from "vitest";

import {
  groupByRow,
  parseRowKey,
  rowHeading,
  rowProgressFor,
} from "../utils/repeatedRows";

/**
 * Reading a row out of a flat indexed key.
 *
 * The backend emits repeated table rows as `children_1_family_name`, because
 * the guided flow asks one question at a time and has no repeated-section UI.
 * On screen that leaves a child's six details looking like six unrelated
 * answers, and "männlich / weiblich" appearing twice with nothing saying whose
 * it is.
 *
 * This is presentation only. Keys are the contract with the backend and with
 * export, and nothing here rewrites one.
 */

describe("parseRowKey", () => {
  it("splits a key into section, index and column", () => {
    expect(parseRowKey("children_1_family_name")).toEqual({
      section: "children",
      index: 1,
      column: "family_name",
      prefix: "children_1_",
    });
  });

  it("handles a section whose own name contains underscores", () => {
    // A greedy leading match would take "spouse" as the section and swallow
    // "details" into the index position.
    expect(parseRowKey("spouse_details_2_passport_number")).toEqual({
      section: "spouse_details",
      index: 2,
      column: "passport_number",
      prefix: "spouse_details_2_",
    });
  });

  it("reads double-digit rows", () => {
    expect(parseRowKey("children_12_gender")?.index).toBe(12);
  });

  it("returns null for an ordinary field key", () => {
    expect(parseRowKey("nom_de_famille")).toBeNull();
    expect(parseRowKey("signature")).toBeNull();
    expect(parseRowKey("")).toBeNull();
  });

  it("returns null for a zero or negative index", () => {
    // Row numbering is 1-based; a `_0_` key is not a row this produced.
    expect(parseRowKey("children_0_name")).toBeNull();
  });
});

describe("groupByRow", () => {
  const keyOf = (k: string) => k;

  it("keeps each row's fields together and in order", () => {
    const { rows } = groupByRow(
      [
        "children_1_family_name",
        "children_1_first_name",
        "children_1_gender",
        "children_2_family_name",
        "children_2_gender",
      ],
      keyOf,
    );

    expect(rows).toHaveLength(2);
    expect(rows[0].items).toEqual([
      "children_1_family_name",
      "children_1_first_name",
      "children_1_gender",
    ]);
    expect(rows[1].items).toEqual([
      "children_2_family_name",
      "children_2_gender",
    ]);
  });

  it("puts rows in ascending index order", () => {
    const { rows } = groupByRow(
      ["children_3_name", "children_1_name", "children_2_name"],
      keyOf,
    );

    expect(rows.map((r) => r.index)).toEqual([1, 2, 3]);
  });

  it("never mixes two rows", () => {
    const { rows } = groupByRow(
      ["children_1_gender", "children_2_gender"],
      keyOf,
    );

    // Selecting one child's gender must not be able to touch another's.
    expect(rows[0].items).toEqual(["children_1_gender"]);
    expect(rows[1].items).toEqual(["children_2_gender"]);
  });

  it("keeps unrelated fields out of any row", () => {
    // Most of a form is not a table.
    const { rows, ungrouped } = groupByRow(
      ["nom_de_famille", "children_1_gender", "signature"],
      keyOf,
    );

    expect(ungrouped).toEqual(["nom_de_famille", "signature"]);
    expect(rows).toHaveLength(1);
  });

  it("separates two different sections on the same page", () => {
    const { rows } = groupByRow(
      ["children_1_name", "spouse_1_name", "children_2_name"],
      keyOf,
    );

    expect(rows).toHaveLength(3);
    expect(new Set(rows.map((r) => r.section))).toEqual(
      new Set(["children", "spouse"]),
    );
  });
});

describe("rowHeading", () => {
  it("singularises a plural section", () => {
    expect(rowHeading("children", 1)).toBe("Child 1");
    expect(rowHeading("children", 2)).toBe("Child 2");
  });

  it("handles other plural shapes", () => {
    expect(rowHeading("dependencies", 1)).toBe("Dependency 1");
    expect(rowHeading("rows", 3)).toBe("Row 3");
  });

  it("leaves a singular section alone", () => {
    expect(rowHeading("spouse", 1)).toBe("Spouse 1");
  });

  it("reads an underscored section as words", () => {
    expect(rowHeading("spouse_details", 2)).toBe("Spouse Detail 2");
  });
});


describe("rowProgressFor", () => {
  const CHILD_1 = [
    "children_1_family_name",
    "children_1_first_name",
    "children_1_gender",
    "children_1_nationality",
  ];
  const CHILD_2 = CHILD_1.map((k) => k.replace("_1_", "_2_"));
  const ALL = ["nom_de_famille", ...CHILD_1, ...CHILD_2, "signature"];

  it("counts position within the row, not within the form", () => {
    // Global progress answers "how much of the form is left", which is the
    // wrong question in the middle of six near-identical questions.
    expect(rowProgressFor("children_1_gender", ALL)).toEqual({
      section: "children",
      index: 1,
      position: 3,
      total: 4,
    });
  });

  it("counts each row separately", () => {
    expect(rowProgressFor("children_2_family_name", ALL)?.position).toBe(1);
    expect(rowProgressFor("children_2_family_name", ALL)?.index).toBe(2);
  });

  it("assumes no particular row length", () => {
    const nine = Array.from(
      { length: 9 },
      (_, i) => `employment_history_3_field${i}`,
    );
    expect(rowProgressFor("employment_history_3_field8", nine)).toEqual({
      section: "employment_history",
      index: 3,
      position: 9,
      total: 9,
    });
  });

  it("counts a row whose fields are not contiguous", () => {
    // Only membership matters, not adjacency — a form may interleave rows.
    const interleaved = [
      "children_1_name",
      "children_2_name",
      "children_1_gender",
    ];
    expect(rowProgressFor("children_1_gender", interleaved)).toEqual({
      section: "children",
      index: 1,
      position: 2,
      total: 2,
    });
  });

  it("reports nothing for an ordinary field", () => {
    expect(rowProgressFor("nom_de_famille", ALL)).toBeNull();
  });

  it("reports nothing rather than a wrong count for a stale field list", () => {
    // "0 of 4" would be worse than no counter at all.
    expect(rowProgressFor("children_9_gender", ALL)).toBeNull();
  });

  it("handles an underscored section", () => {
    const keys = ["spouse_details_2_passport", "spouse_details_2_issued_on"];
    expect(rowProgressFor("spouse_details_2_issued_on", keys)).toEqual({
      section: "spouse_details",
      index: 2,
      position: 2,
      total: 2,
    });
  });
});
