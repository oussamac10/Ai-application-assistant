import { describe, it, expect } from "vitest";

import {
  extractExportErrorCode,
  resolveExportError,
} from "../utils/resolveExportErrorMessage";

/**
 * What a failed export tells the user.
 *
 * The screen previously showed `error.detail` — whatever string the backend
 * happened to send — for anything that was not a 401 or a 422. That is both
 * unhelpful and unsafe: a detail field is the wrong thing to trust, because one
 * careless `raise` upstream puts a library message or a file path on screen.
 *
 * Nothing from the response is rendered. An allowlist maps known codes to
 * translated sentences and everything else falls back to one generic message.
 */

const t = (key: string) => key;

describe("extractExportErrorCode", () => {
  it("reads a code from any of the shapes the API produces", () => {
    expect(extractExportErrorCode({ errorCode: "export_forbidden" })).toBe(
      "export_forbidden",
    );
    expect(extractExportErrorCode({ error_code: "signature_invalid" })).toBe(
      "signature_invalid",
    );
    expect(extractExportErrorCode({ detail: "signature_too_large" })).toBe(
      "signature_too_large",
    );
  });

  it("ignores a detail that is not a known code", () => {
    // The whole point: an arbitrary sentence must never become the message.
    expect(
      extractExportErrorCode({
        detail: "PDF rendering failed: /tmp/exports/abc.pdf missing",
      }),
    ).toBeNull();
  });

  it("never throws on an unexpected shape", () => {
    expect(extractExportErrorCode(null)).toBeNull();
    expect(extractExportErrorCode("boom")).toBeNull();
    expect(extractExportErrorCode(42)).toBeNull();
    expect(extractExportErrorCode({})).toBeNull();
  });
});

describe("resolveExportError", () => {
  it.each([
    "export_forbidden",
    "signature_mapping_missing",
    "signature_invalid",
    "signature_too_large",
    "signature_export_failed",
    "template_mapping_invalid",
  ])("gives %s its own message", (code) => {
    expect(resolveExportError(t, { errorCode: code }).message).toBe(
      `error_${code}`,
    );
  });

  it("falls back to one generic message for an unknown failure", () => {
    expect(resolveExportError(t, { errorCode: "something_new" }).message).toBe(
      "exportFailed",
    );
    expect(resolveExportError(t, new Error("kaboom")).message).toBe(
      "exportFailed",
    );
  });

  it("never renders backend text, however it arrives", () => {
    const leaky = {
      detail: "Traceback (most recent call last): /srv/app/pdf/services.py",
    };

    expect(resolveExportError(t, leaky).message).toBe("exportFailed");
  });

  it("offers re-signing only where signing again would help", () => {
    // A signature that is invalid, oversized or unrenderable is the user's to
    // fix.
    for (const code of [
      "signature_invalid",
      "signature_too_large",
      "signature_export_failed",
    ]) {
      expect(resolveExportError(t, { errorCode: code }).canResign).toBe(true);
    }

    // A missing rectangle or a broken mapping is a fault in the template.
    // Sending someone back to sign again would waste their time on something
    // they cannot fix.
    for (const code of ["signature_mapping_missing", "template_mapping_invalid"]) {
      expect(resolveExportError(t, { errorCode: code }).canResign).toBe(false);
    }
  });

  it("does not offer a retry that cannot succeed", () => {
    expect(resolveExportError(t, { errorCode: "export_forbidden" }).canRetry).toBe(
      false,
    );
    expect(
      resolveExportError(t, { errorCode: "template_mapping_invalid" }).canRetry,
    ).toBe(false);
  });

  it("keeps retry available for a transient failure", () => {
    expect(
      resolveExportError(t, { errorCode: "signature_export_failed" }).canRetry,
    ).toBe(true);
    expect(resolveExportError(t, new Error("network")).canRetry).toBe(true);
  });

  it("never puts signature coordinates on screen", () => {
    const withCoordinates = {
      detail: "signature at [[123.5, 456.75], [789.0, 12.25]] is out of bounds",
    };

    const message = resolveExportError(t, withCoordinates).message;

    expect(message).toBe("exportFailed");
    expect(message).not.toContain("123.5");
    expect(message).not.toContain("456.75");
  });
});
