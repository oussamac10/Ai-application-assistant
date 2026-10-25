import { describe, it, expect } from "vitest";
import {
  extractErrorCode,
  resolveUploadErrorMessage,
} from "../utils/resolveUploadErrorMessage";

// Mirrors how tests elsewhere in this repo stub next-intl: t(key) returns
// the bare key, exactly like the real library does when scoped under
// useTranslations("documentUpload") — i.e. it does NOT return the
// "documentUpload.<key>" namespaced form here, matching the mocking
// convention already used by DocumentUploadForm's own tests.
const identityT = (key: string) => key;

describe("extractErrorCode", () => {
  it("reads a string detail field", () => {
    expect(extractErrorCode({ detail: "invalid_file_type" })).toBe(
      "invalid_file_type"
    );
  });

  it("reads a top-level code field", () => {
    expect(extractErrorCode({ code: "file_too_large" })).toBe("file_too_large");
  });

  it("reads a nested error.code field", () => {
    expect(extractErrorCode({ error: { code: "malformed_pdf" } })).toBe(
      "malformed_pdf"
    );
  });

  it("falls back to message when no detail/code is present", () => {
    expect(extractErrorCode({ message: "unavailable" })).toBe("unavailable");
  });

  it("returns null for a null detail", () => {
    expect(extractErrorCode({ detail: null })).toBeNull();
  });

  it("returns null for an object with no recognized shape", () => {
    expect(extractErrorCode({ foo: "bar" })).toBeNull();
  });

  it("returns null for null/undefined input", () => {
    expect(extractErrorCode(null)).toBeNull();
    expect(extractErrorCode(undefined)).toBeNull();
  });
});

describe("resolveUploadErrorMessage", () => {
  it("uses the generic translated fallback when the error detail is null", () => {
    const msg = resolveUploadErrorMessage(identityT, { detail: null });
    expect(msg).toBe("error_generic_fallback");
    expect(msg).not.toContain("null");
    expect(msg).not.toMatch(/^documentUpload\./);
  });

  it("uses the generic translated fallback for an unrecognized error code", () => {
    const msg = resolveUploadErrorMessage(identityT, {
      detail: "some_unmapped_backend_code",
    });
    expect(msg).toBe("error_generic_fallback");
  });

  it("uses the specific translation for a known error code", () => {
    const msg = resolveUploadErrorMessage(identityT, {
      detail: "invalid_file_type",
    });
    expect(msg).toBe("error_invalid_file_type");
    expect(
      resolveUploadErrorMessage(identityT, { detail: "image_too_large" })
    ).toBe("error_image_too_large");
  });

  it("uses the generic fallback for a completely malformed error value", () => {
    expect(resolveUploadErrorMessage(identityT, undefined)).toBe(
      "error_generic_fallback"
    );
    expect(resolveUploadErrorMessage(identityT, {})).toBe(
      "error_generic_fallback"
    );
    expect(resolveUploadErrorMessage(identityT, "some raw string")).toBe(
      // Bare strings are treated as a candidate code too — still must
      // resolve to the generic fallback since it isn't in the allowlist.
      "error_generic_fallback"
    );
  });

  it("never returns a raw namespaced translation key", () => {
    const t = (key: string) => `documentUpload.${key}`; // simulates a missing message
    const msg = resolveUploadErrorMessage(t, { detail: null });
    // Even if t() itself would produce the raw missing-key format for an
    // unmapped code, resolveUploadErrorMessage must never even attempt an
    // unrecognized code — it always calls t() with the safe generic key.
    expect(msg).toBe("documentUpload.error_generic_fallback");
  });
});
