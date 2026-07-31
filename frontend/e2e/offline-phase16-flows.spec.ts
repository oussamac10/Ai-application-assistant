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
