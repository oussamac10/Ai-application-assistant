import { describe, it, expect } from "vitest";
import {
  formatOriginalAnswer,
  formatProposedValue,
} from "../utils/formatProposedValue";

describe("formatProposedValue", () => {
  it("prefers a non-empty outputValue", () => {
    expect(formatProposedValue("ignored", "I am married", "multiline_text")).toBe(
      "I am married"
    );
  });

  it("renders a plain string normalizedValue as-is when outputValue is missing", () => {
    expect(formatProposedValue("I am married", null, "multiline_text")).toBe(
      "I am married"
    );
  });

  it("renders numbers as plain strings and booleans as human-readable Yes/No", () => {
    expect(formatProposedValue(42, null, "integer")).toBe("42");
    expect(formatProposedValue(true, null, "boolean")).toBe("Yes");
    expect(formatProposedValue(false, null, "boolean")).toBe("No");
    expect(formatProposedValue(true, "True", "boolean")).toBe("Yes");
    expect(formatProposedValue(true, "Oui", "boolean")).toBe("Oui");
  });

  it("joins an array normalizedValue for display", () => {
    expect(
      formatProposedValue(["Housing", "Education"], null, "multiple_choice")
    ).toBe("Housing, Education");
  });

  it("returns an empty string for null/undefined normalizedValue", () => {
    expect(formatProposedValue(null, null, "string")).toBe("");
    expect(formatProposedValue(undefined, undefined, "string")).toBe("");
  });

  it("never renders a raw object for an unexpected shape/field type", () => {
    const reasoningKey =
      "The user's answer 'Je suis marié' translates to 'I am married' " +
      "in French, but the field is a multiline_text field...";
    const malformed = { [reasoningKey]: "marié" };
    const result = formatProposedValue(malformed, null, "multiline_text");
    expect(result).toBe("");
    expect(result).not.toContain("translates to");
  });

  it("never renders [object Object] for an unhandled object shape", () => {
    const result = formatProposedValue({ unexpectedKey: "value" }, null, "string");
    expect(result).not.toContain("[object Object]");
    expect(result).not.toContain("{");
  });

  it("formats a documented person_name object using fullName", () => {
    expect(
      formatProposedValue(
        { fullName: "Jane Doe", givenName: "Jane", familyName: "Doe" },
        null,
        "person_name"
      )
    ).toBe("Jane Doe");
  });

  it("formats a documented money object into a readable summary and omits 'once' and '.0'", () => {
    expect(
      formatProposedValue(
        { amount: 1800, currency: "EUR", period: "monthly" },
        null,
        "money"
      )
    ).toBe("1800 EUR monthly");
    expect(
      formatProposedValue(
        { amount: 2000.0, currency: "EUR", period: "once" },
        "2000.0 EUR once",
        "money"
      )
    ).toBe("2000 EUR");
  });

  it("falls back safely when a documented structured type has an unusable shape", () => {
    expect(formatProposedValue({ currency: "EUR" }, null, "money")).toBe("");
    expect(formatProposedValue({}, null, "person_name")).toBe("");
  });
});

describe("formatOriginalAnswer", () => {
  it("formats multiple_choice JSON arrays into comma-separated labels", () => {
    expect(
      formatOriginalAnswer(
        '["Curriculum vitae","Attestation d\'inscription"]',
        "multiple_choice"
      )
    ).toBe("Curriculum vitae, Attestation d'inscription");
  });

  it("formats boolean raw strings into Yes/No", () => {
    expect(formatOriginalAnswer("true", "boolean")).toBe("Yes");
    expect(formatOriginalAnswer("false", "boolean")).toBe("No");
  });
});
