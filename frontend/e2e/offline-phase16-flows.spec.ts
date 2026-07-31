/**
 * Phase 16 flows, driven entirely offline.
 *
 * Every request is intercepted (`e2e/fixtures/mockSession.ts`), so this suite
 * needs no Azure credentials, spends no Document Intelligence quota, and does
 * not depend on what a detector happened to find in a PDF. The behaviours under
 * test are frontend behaviours; the backend contracts they rely on are covered
 * directly by the backend suite.
 *
 * The live-Azure specs remain separate and opt-in — see the other files in
 * `e2e/`, which drive the real stack and are the ones that consume quota.
 */

import { test, expect } from "@playwright/test";
import { drawSignature, mockGuidedSession } from "./fixtures/mockSession";

const SESSION = "offline-session";

test.describe("Phase 16 — offline flows (no Azure)", () => {
  test.describe.configure({ timeout: 60_000 });

  // ------------------------------------------------------------------
  // Signature
  // ------------------------------------------------------------------

  test("a signature question renders a pad, not a text input", async ({ page }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f-sig",
          key: "signature",
          fieldType: "signature",
          required: true,
          requiredness: "required",
          signatureRequirement: "required_before_submission",
          position: 1,
          label: "Signature",
        },
      ],
    });

    await page.goto(`/application/session/${SESSION}`);

    await expect(page.getByTestId("signature-canvas")).toBeVisible();
    await expect(page.getByTestId("signature-sign-after-printing")).toBeEnabled();
    // A signature is drawn, never typed.
    await expect(page.locator("form input[type='text']")).toHaveCount(0);
  });

  test("drawing enables Clear and Undo, and Clear removes the signature", async ({
    page,
  }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f-sig",
          key: "signature",
          fieldType: "signature",
          required: false,
          requiredness: "unknown",
          position: 1,
          label: "Signature",
        },
      ],
    });
    await page.goto(`/application/session/${SESSION}`);
    await expect(page.getByTestId("signature-canvas")).toBeVisible();

    await expect(page.getByTestId("signature-clear")).toBeDisabled();

    await drawSignature(page);

    await expect(page.getByTestId("signature-clear")).toBeEnabled();
    await expect(page.getByTestId("signature-undo")).toBeEnabled();

    await page.getByTestId("signature-clear").click();
    await expect(page.getByTestId("signature-clear")).toBeDisabled();
  });

  test("Sign after printing is offered even for a required signature", async ({
    page,
  }) => {
    // The product rule: a required signature box means the *printed* form must
    // be signed, never that it must be signed here.
    const { log } = await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f-sig",
          key: "signature",
          fieldType: "signature",
          required: true,
          requiredness: "required",
          signatureRequirement: "required_before_submission",
          position: 1,
          label: "Signature",
        },
        {
          id: "f-next",
          key: "nom",
          fieldType: "string",
          required: false,
          requiredness: "unknown",
          position: 2,
          label: "Nom",
        },
      ],
    });
    await page.goto(`/application/session/${SESSION}`);

    await page.getByTestId("signature-sign-after-printing").click();

    await expect
      .poll(() => log.matching("/sign-after-printing").length)
      .toBeGreaterThan(0);
    // And it advances, rather than stranding the user on the signature.
    await expect(page.getByText("Nom")).toBeVisible();
  });

  test("a deferred signature is reported as such before download", async ({
    page,
  }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f-sig",
          key: "signature",
          fieldType: "signature",
          required: true,
          position: 1,
          label: "Signature",
        },
      ],
      summary: [
        {
          fieldId: "f-sig",
          fieldKey: "signature",
          label: "Signature",
          required: true,
          requiredness: "required",
          originalAnswer: null,
          outputValue: null,
          status: "pending_manual_signature",
          answerState: "pending_manual_signature",
        },
      ],
    });

    await page.goto(`/application/session/${SESSION}/complete`);

    await expect(
      page.getByTestId("handwritten-signature-reminder"),
    ).toBeVisible();
  });

  test("a digitally signed form shows no handwriting reminder", async ({
    page,
  }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f-sig",
          key: "signature",
          fieldType: "signature",
          required: true,
          position: 1,
          label: "Signature",
        },
      ],
      summary: [
        {
          fieldId: "f-sig",
          fieldKey: "signature",
          label: "Signature",
          required: true,
          requiredness: "required",
          originalAnswer: null,
          outputValue: null,
          status: "confirmed",
          answerState: "answered",
        },
      ],
    });

    await page.goto(`/application/session/${SESSION}/complete`);
    await page.waitForLoadState("networkidle");

    // Telling someone who signed to sign again suggests it did not take.
    await expect(
      page.getByTestId("handwritten-signature-reminder"),
    ).toHaveCount(0);
  });

  // ------------------------------------------------------------------
  // Currency
  // ------------------------------------------------------------------

  test("a euro field proposes EUR, and the frontend invents nothing", async ({
    page,
  }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f-money",
          key: "revenu",
          fieldType: "string",
          required: false,
          requiredness: "unknown",
          position: 1,
          label: "Revenu net mensuel en euros",
        },
      ],
      answerResponse: {
        id: "a1",
        fieldId: "f-money",
        originalAnswer: "2000",
        // Resolved by the backend. The UI's job is to show it unchanged.
        outputValue: "2000 EUR",
        normalizedValue: { amount: 2000, currency: "EUR" },
        status: "awaiting_confirmation",
        validationStatus: "valid",
      },
    });
    await page.goto(`/application/session/${SESSION}`);

    await page.locator("form input, form textarea").first().fill("2000");
    await page.getByRole("button", { name: /continue/i }).click();

    await expect(page.getByText("2000 EUR")).toBeVisible();
  });

  test("an unknown currency context never shows USD", async ({ page }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f-money",
          key: "income",
          fieldType: "string",
          required: false,
          requiredness: "unknown",
          position: 1,
          label: "Monthly income",
        },
      ],
      answerResponse: {
        id: "a1",
        fieldId: "f-money",
        originalAnswer: "2000",
        // No currency: the backend removed the invented one.
        outputValue: "2000",
        normalizedValue: { amount: 2000 },
        status: "awaiting_confirmation",
        validationStatus: "valid",
      },
    });
    await page.goto(`/application/session/${SESSION}`);

    await page.locator("form input, form textarea").first().fill("2000");
    await page.getByRole("button", { name: /continue/i }).click();

    await expect(page.getByText("2000", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/USD/)).toHaveCount(0);
  });

  // ------------------------------------------------------------------
  // Requiredness and Skip
  // ------------------------------------------------------------------

  test("an unmarked question shows no requiredness label but can be skipped", async ({
    page,
  }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f1",
          key: "nom",
          fieldType: "string",
          required: false,
          requiredness: "unknown",
          position: 1,
          label: "Nom de famille",
        },
        {
          id: "f2",
          key: "prenom",
          fieldType: "string",
          required: false,
          requiredness: "optional",
          position: 2,
          label: "Prenom",
        },
      ],
    });
    await page.goto(`/application/session/${SESSION}`);

    // Saying "Optional" here would claim something the document never said.
    await expect(page.getByTestId("requiredness")).toHaveCount(0);
    await expect(page.getByTestId("skip-question")).toBeEnabled();

    await page.getByTestId("skip-question").click();

    await expect(page.getByTestId("requiredness")).toHaveText(/optional/i);
  });

  test("a required question offers no Skip", async ({ page }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f1",
          key: "nom",
          fieldType: "string",
          required: true,
          requiredness: "required",
          position: 1,
          label: "Nom de famille",
        },
      ],
    });
    await page.goto(`/application/session/${SESSION}`);

    await expect(page.getByTestId("requiredness")).toHaveText(/required/i);
    await expect(page.getByTestId("skip-question")).toHaveCount(0);
  });

  // ------------------------------------------------------------------
  // Repeated child rows
  // ------------------------------------------------------------------

  test("each child row's gender is its own question", async ({ page }) => {
    // Two rows, each with its own indexed gender key. Selecting one must not
    // touch the other, which is exactly what a shared question would do.
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "g1",
          key: "children_1_gender",
          fieldType: "single_choice",
          required: false,
          requiredness: "unknown",
          position: 1,
          label: "Children 1 — männlich / weiblich",
          options: [
            { value: "männlich", label: "männlich" },
            { value: "weiblich", label: "weiblich" },
          ],
        },
        {
          id: "g2",
          key: "children_2_gender",
          fieldType: "single_choice",
          required: false,
          requiredness: "unknown",
          position: 2,
          label: "Children 2 — männlich / weiblich",
          options: [
            { value: "männlich", label: "männlich" },
            { value: "weiblich", label: "weiblich" },
          ],
        },
      ],
    });
    await page.goto(`/application/session/${SESSION}`);

    // Row 1 comes first and names itself.
    await expect(page.getByText("Children 1 — männlich / weiblich")).toBeVisible();
    await expect(page.getByText("Children 2 — männlich / weiblich")).toHaveCount(0);

    await page.getByTestId("skip-question").click();

    // Row 2 is a separate question, in order.
    await expect(page.getByText("Children 2 — männlich / weiblich")).toBeVisible();
  });

  // ------------------------------------------------------------------
  // The point of the whole file
  // ------------------------------------------------------------------

  test("the offline suite reaches no third-party service", async ({ page }) => {
    const external: string[] = [];
    page.on("request", (request) => {
      const url = request.url();
      if (!url.startsWith("http://localhost") && !url.startsWith("data:")) {
        external.push(url);
      }
    });

    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f1",
          key: "nom",
          fieldType: "string",
          required: false,
          position: 1,
          label: "Nom",
        },
      ],
    });
    await page.goto(`/application/session/${SESSION}`);
    await page.waitForLoadState("networkidle");

    expect(external).toEqual([]);
  });
});

test.describe("Phase 16 — offline export and repeated rows", () => {
  test.describe.configure({ timeout: 60_000 });

  const CHILD_ROWS = [
    {
      fieldId: "c1n",
      fieldKey: "children_1_family_name",
      label: "Familienname",
      required: false,
      requiredness: "unknown",
      originalAnswer: "Muster",
      outputValue: "Muster",
      status: "confirmed",
      answerState: "answered",
    },
    {
      fieldId: "c1g",
      fieldKey: "children_1_gender",
      label: "männlich / weiblich",
      required: false,
      requiredness: "unknown",
      originalAnswer: "männlich",
      outputValue: "männlich",
      status: "confirmed",
      answerState: "answered",
    },
    {
      fieldId: "c2n",
      fieldKey: "children_2_family_name",
      label: "Familienname",
      required: false,
      requiredness: "unknown",
      originalAnswer: "Beispiel",
      outputValue: "Beispiel",
      status: "confirmed",
      answerState: "answered",
    },
    {
      fieldId: "c2g",
      fieldKey: "children_2_gender",
      label: "männlich / weiblich",
      required: false,
      requiredness: "unknown",
      originalAnswer: "weiblich",
      outputValue: "weiblich",
      status: "confirmed",
      answerState: "answered",
    },
  ];

  // ------------------------------------------------------------------
  // Export
  // ------------------------------------------------------------------

  test("a digitally signed form exports and downloads", async ({ page }) => {
    const { log } = await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f-sig",
          key: "signature",
          fieldType: "signature",
          required: true,
          position: 1,
          label: "Signature",
        },
      ],
      summary: [
        {
          fieldId: "f-sig",
          fieldKey: "signature",
          label: "Signature",
          required: true,
          requiredness: "required",
          originalAnswer: null,
          outputValue: null,
          status: "confirmed",
          answerState: "answered",
        },
      ],
    });

    await page.goto(`/application/session/${SESSION}/complete`);
    await page.waitForLoadState("networkidle");

    // Someone who signed must not be told to sign again.
    await expect(page.getByTestId("handwritten-signature-reminder")).toHaveCount(0);

    await page.getByRole("button", { name: /generate|export|download/i }).first().click();

    await expect.poll(() => log.matching("/exports").length).toBeGreaterThan(0);
  });

  test("a form signed on paper still exports", async ({ page }) => {
    const { log } = await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f-sig",
          key: "signature",
          fieldType: "signature",
          required: true,
          position: 1,
          label: "Signature",
        },
      ],
      summary: [
        {
          fieldId: "f-sig",
          fieldKey: "signature",
          label: "Signature",
          required: true,
          requiredness: "required",
          originalAnswer: null,
          outputValue: null,
          status: "pending_manual_signature",
          answerState: "pending_manual_signature",
        },
      ],
    });

    await page.goto(`/application/session/${SESSION}/complete`);

    // The reminder is shown *and* the export stays available — deferring is a
    // completion, not a blocker.
    await expect(page.getByTestId("handwritten-signature-reminder")).toBeVisible();

    await page.getByRole("button", { name: /generate|export|download/i }).first().click();

    await expect.poll(() => log.matching("/exports").length).toBeGreaterThan(0);
  });

  test("a failed export is reported readably and can be retried", async ({
    page,
  }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f-sig",
          key: "signature",
          fieldType: "signature",
          required: true,
          position: 1,
          label: "Signature",
        },
      ],
      exportError: { status: 422, code: "signature_mapping_missing" },
    });

    await page.goto(`/application/session/${SESSION}/complete`);
    const button = page
      .getByRole("button", { name: /generate|export|download/i })
      .first();
    await button.click();

    // The user stays here and can try again, rather than being dropped.
    await expect(button).toBeVisible();
    // And no internal detail is on screen.
    const text = await page.locator("body").innerText();
    expect(text).not.toMatch(/Traceback|pypdf|\/tmp\//);
  });

  // ------------------------------------------------------------------
  // Repeated row headings
  // ------------------------------------------------------------------

  test("the summary groups each child's fields under its own heading", async ({
    page,
  }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "c1n",
          key: "children_1_family_name",
          fieldType: "string",
          required: false,
          position: 1,
          label: "Familienname",
        },
      ],
      summary: CHILD_ROWS,
    });

    await page.goto(`/application/session/${SESSION}/summary`);

    await expect(page.getByTestId("row-heading-children-1")).toHaveText("Child 1");
    await expect(page.getByTestId("row-heading-children-2")).toHaveText("Child 2");

    // Each child's own gender sits in its own row, with its own value.
    await expect(
      page.getByTestId("summary-row-children_1_gender"),
    ).toContainText("männlich");
    await expect(
      page.getByTestId("summary-row-children_2_gender"),
    ).toContainText("weiblich");
  });

  test("a heading is not itself an answer row", async ({ page }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "c1n",
          key: "children_1_family_name",
          fieldType: "string",
          required: false,
          position: 1,
          label: "Familienname",
        },
      ],
      summary: CHILD_ROWS,
    });

    await page.goto(`/application/session/${SESSION}/summary`);

    // Four answers, two headings — the headings must not add editable rows.
    await expect(page.getByRole("button", { name: "edit" })).toHaveCount(4);
  });

  // ------------------------------------------------------------------
  // Guided flow row context
  // ------------------------------------------------------------------

  test("the guided flow says which child a question is about", async ({ page }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "c2g",
          key: "children_2_gender",
          fieldType: "single_choice",
          required: false,
          requiredness: "unknown",
          position: 1,
          label: "männlich / weiblich",
          options: [
            { value: "männlich", label: "männlich" },
            { value: "weiblich", label: "weiblich" },
          ],
        },
      ],
    });

    await page.goto(`/application/session/${SESSION}`);

    // Without this the screen just says "männlich / weiblich" with nothing
    // saying whose. The row counter is nested inside the same element, so
    // match the heading rather than the whole string.
    await expect(page.getByTestId("row-context")).toContainText("Child 2");
  });

  test("the guided flow says how far through a child's details you are", async ({
    page,
  }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "c1g",
          key: "children_1_gender",
          fieldType: "single_choice",
          required: false,
          position: 1,
          label: "männlich / weiblich",
          options: [
            { value: "männlich", label: "männlich" },
            { value: "weiblich", label: "weiblich" },
          ],
        },
      ],
      summary: CHILD_ROWS,
    });

    await page.goto(`/application/session/${SESSION}`);

    // Global progress answers "how much of the form is left"; this answers
    // "how much of this child is left".
    await expect(page.getByTestId("row-progress")).toHaveText("Field 2 of 2");
  });

  test("an ordinary question shows no row context", async ({ page }) => {
    await mockGuidedSession(page, {
      sessionId: SESSION,
      fields: [
        {
          id: "f1",
          key: "nom_de_famille",
          fieldType: "string",
          required: false,
          position: 1,
          label: "Nom de famille",
        },
      ],
    });

    await page.goto(`/application/session/${SESSION}`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByTestId("row-context")).toHaveCount(0);
  });
});
