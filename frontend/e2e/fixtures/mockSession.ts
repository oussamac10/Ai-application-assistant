import { Page, Route } from "@playwright/test";

/**
 * Deterministic guided-session data, served by intercepting `/api/**`.
 *
 * The existing E2E specs drive the real backend, which means every one of them
 * uploads a PDF and spends Azure Document Intelligence quota — on an F0 tier
 * that rate-limits after a handful of requests, so the suite became both slow
 * and flaky for reasons that had nothing to do with the code under test.
 *
 * The behaviours this file covers are frontend behaviours: does a signature
 * field render a pad, does Continue stay disabled until required declarations
 * are checked, does the confirmation screen show the currency the backend
 * resolved. None of that needs a real document, and pinning the data makes the
 * assertions exact rather than dependent on what a detector happened to find.
 *
 * Backend contracts stay covered by the backend suite, which tests them
 * directly and far more cheaply than a browser can.
 */

export type MockField = {
  id: string;
  key: string;
  fieldType: string;
  required: boolean;
  requiredness?: string;
  position: number;
  label: string;
  options?: Array<{ value: string; label: string }> | null;
  signatureRequirement?: string | null;
  digitalSignatureRequired?: boolean;
  currentAnswerStatus?: string | null;
};

export type MockSummaryRow = {
  fieldId: string;
  fieldKey: string;
  label: string;
  required: boolean;
  requiredness?: string;
  originalAnswer: string | null;
  outputValue: string | null;
  status: string;
  answerState?: string;
};

export interface MockSessionOptions {
  /** Fail the export with this code instead of succeeding. Lets a spec check
   * that the UI reports a structured failure readably and lets the user try
   * again, without needing a backend that can fail on demand. */
  exportError?: { status: number; code: string };
  sessionId?: string;
  fields: MockField[];
  summary?: MockSummaryRow[];
  /** What `POST /answers` returns. Defaults to an accepted answer awaiting
   * confirmation, which is the ordinary path. */
  answerResponse?: Record<string, unknown>;
  totalQuestions?: number;
  answeredQuestions?: number;
}

/** Every request the mocked session received, so a test can assert that a
 * particular call was made — or that none reached a paid service. */
export class RequestLog {
  readonly urls: string[] = [];

  record(url: string) {
    this.urls.push(url);
  }

  /** Requests whose path contains `fragment`. */
  matching(fragment: string): string[] {
    return this.urls.filter((url) => url.includes(fragment));
  }
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function fieldPayload(
  field: MockField,
  total: number,
  answered: number,
  summaryRows: MockSummaryRow[] = [],
): Record<string, unknown> {
  const row = summaryRows.find((r) => r.fieldId === field.id);
  return {
    id: field.id,
    fieldId: field.id,
    key: field.key,
    fieldKey: field.key,
    fieldType: field.fieldType,
    required: field.required,
    requiredness: field.requiredness ?? (field.required ? "required" : "unknown"),
    signatureRequirement: field.signatureRequirement ?? null,
    digitalSignatureRequired: field.digitalSignatureRequired ?? false,
    position: field.position,
    label: field.label,
    helpText: null,
    placeholder: null,
    options: field.options ?? null,
    currentAnswerStatus: field.currentAnswerStatus ?? null,
    originalAnswer: row?.originalAnswer ?? null,
    allFieldKeys: summaryRows.map((r) => r.fieldKey),
    progress: {
      confirmedRequiredFields: answered,
      totalRequiredFields: total,
      totalQuestions: total,
      answeredQuestions: answered,
      percentage: total ? Math.round((answered / total) * 100) : 0,
    },
  };
}

/**
 * Installs the mock. Returns the session id and a request log.
 *
 * State lives in the closure: advancing past a question, skipping and
 * deferring a signature all move a cursor, so a spec can walk the flow exactly
 * as a user would rather than asserting against a frozen snapshot.
 */
export async function mockGuidedSession(
  page: Page,
  options: MockSessionOptions,
): Promise<{ sessionId: string; log: RequestLog }> {
  const sessionId = options.sessionId ?? "e2e-session";
  const log = new RequestLog();
  const fields = options.fields;
  let cursor = 0;
  let answered = 0;

  const summaryRows: MockSummaryRow[] =
    options.summary ??
    fields.map((field) => ({
      fieldId: field.id,
      fieldKey: field.key,
      label: field.label,
      required: field.required,
      requiredness: field.requiredness,
      originalAnswer: null,
      outputValue: null,
      status: "unanswered",
      answerState: "unreached",
    }));

  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    log.record(path);

    // `startSession` validates the full session schema, not just a status —
    // a thin `{status}` reply fails Zod and the page renders an error instead
    // of the question.
    const sessionPayload = {
      publicId: sessionId,
      status: "in_progress",
      userLanguage: "en",
      outputLanguage: "en",
      expiresAt: new Date(Date.now() + 86_400_000).toISOString(),
      exportSupported: true,
    };

    if (path.endsWith("/start")) {
      return json(route, sessionPayload);
    }

    if (path.endsWith("/current-field")) {
      const field = fields[Math.min(cursor, fields.length - 1)];
      return json(
        route,
        fieldPayload(field, fields.length, answered, summaryRows),
      );
    }

    if (path.endsWith("/summary")) {
      return json(route, { fields: summaryRows });
    }

    if (path.endsWith("/sign-after-printing")) {
      const field = fields[cursor];
      const row = summaryRows.find((r) => r.fieldId === field.id);
      if (row) {
        row.status = "pending_manual_signature";
        row.answerState = "pending_manual_signature";
      }
      answered += 1;
      cursor = Math.min(cursor + 1, fields.length - 1);
      return json(route, {
        id: "answer-signature",
        fieldId: field.id,
        originalAnswer: null,
        normalizedValue: null,
        outputValue: null,
        status: "pending_manual_signature",
        validationStatus: "not_checked",
      });
    }

    if (path.endsWith("/signature")) {
      const field = fields[cursor];
      const row = summaryRows.find((r) => r.fieldId === field.id);
      if (row) {
        row.status = "awaiting_confirmation";
        row.answerState = "answered";
      }
      return json(route, {
        id: "answer-signature",
        fieldId: field.id,
        originalAnswer: null,
        normalizedValue: { strokes: [], width: 600, height: 200 },
        outputValue: null,
        status: "awaiting_confirmation",
        validationStatus: "valid",
      });
    }

    if (path.endsWith("/skip")) {
      answered += 1;
      cursor = Math.min(cursor + 1, fields.length - 1);
      return json(route, {
        id: "answer-skip",
        originalAnswer: null,
        normalizedValue: null,
        outputValue: null,
        status: "skipped",
        validationStatus: "not_checked",
      });
    }

    if (path.endsWith("/answers")) {
      const field = fields[cursor];
      const body = route.request().postDataJSON?.() ?? {};
      const row = summaryRows.find((r) => r.fieldId === field.id);
      if (row) {
        row.originalAnswer = body.originalAnswer ?? null;
        row.status = "awaiting_confirmation";
        row.answerState = "answered";
      }
      return json(
        route,
        options.answerResponse ?? {
          id: "answer-1",
          fieldId: field.id,
          originalAnswer: body.originalAnswer ?? null,
          // The proposed value comes from the backend, already normalized.
          // The frontend must render it and never invent its own currency.
          outputValue: row?.outputValue ?? body.originalAnswer ?? null,
          normalizedValue: null,
          status: "awaiting_confirmation",
          validationStatus: "valid",
        },
      );
    }

    if (path.includes("/answers/") && path.endsWith("/confirm")) {
      answered += 1;
      cursor = Math.min(cursor + 1, fields.length - 1);
      return json(route, {
        id: "answer-1",
        originalAnswer: null,
        status: "confirmed",
        validationStatus: "valid",
      });
    }

    if (path.endsWith("/confirm-summary")) {
      return json(route, { status: "ready_for_export" });
    }

    if (path.endsWith("/exports")) {
      if (options.exportError) {
        return json(
          route,
          { detail: options.exportError.code, error_code: options.exportError.code },
          options.exportError.status,
        );
      }
      return json(route, {
        exportId: "export-1",
        status: "completed",
        fileName: "form.pdf",
        contentType: "application/pdf",
        fileSize: 1234,
        downloadUrl: `/api/form-sessions/${sessionId}/exports/export-1/download`,
        expiresAt: new Date(Date.now() + 86_400_000).toISOString(),
      });
    }

    if (path.includes("/exports/") && path.endsWith("/download")) {
      // A minimal but genuinely valid PDF, so the browser handles a real
      // download rather than a string pretending to be one.
      return route.fulfill({
        status: 200,
        contentType: "application/pdf",
        body: "%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF",
      });
    }

    if (path.match(/\/form-sessions\/[^/]+$/)) {
      return json(route, { ...sessionPayload, status: "ready_for_export" });
    }

    // Anything unrecognised fails loudly rather than silently reaching a real
    // service — a mock that quietly falls through is worse than no mock.
    return json(route, { detail: `unmocked: ${path}` }, 501);
  });

  return { sessionId, log };
}

/** Draws a deterministic stroke on the signature pad.
 *
 * Pointer Events only, matching the component. Simple geometry on purpose:
 * the tests assert that *a* signature was captured, never anything about its
 * shape — biometric detail has no place in a test fixture. */
export async function drawSignature(page: Page) {
  const canvas = page.getByTestId("signature-canvas");
  const box = await canvas.boundingBox();
  if (!box) throw new Error("signature canvas has no layout box");

  await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.3);
  await page.mouse.move(box.x + box.width * 0.8, box.y + box.height * 0.6);
  await page.mouse.up();
}
