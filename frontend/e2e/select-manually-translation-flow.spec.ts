/**
 * Playwright regression for the "Select Manually" language-inconsistency
 * fix: manually-selected predefined forms must display guided questions
 * in user_language, independent of the form's own (source) language and
 * of output_language — not just Upload Form sessions.
 *
 * Scenario A: German user language + English output language, select an
 *   existing English-only predefined form manually, verify the question
 *   displays translated (not the literal English source text).
 * Scenario B: same form, Arabic user language — verify Arabic display and
 *   that html dir="rtl" stays active throughout.
 * Scenario C: Upload Form flow still behaves as before (unaffected by this
 *   fix) — a minimal smoke check, not a duplicate of the full detection
 *   suite in dynamic-field-detection-flow.spec.ts.
 *
 * These exercise the real Ollama translation call end-to-end (no mocked
 * AI provider), so — like the Upload Form multilingual tests — they never
 * assert exact translated wording (LLM phrasing can vary); they assert the
 * invariants that matter: displayed text differs from the raw English
 * source, and RTL / stable behavior hold.
 */

import { test, expect, Page, APIRequestContext } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";

const RUN_ID = Date.now();
const FIXTURE_FORM_KEY = `select-manually-en-only-${RUN_ID}`;
const FIXTURE_FORM_NAME = `Playwright Manual EN Only ${RUN_ID}`;
const FIXTURE_FORM_OPTION_LABEL = `${FIXTURE_FORM_NAME} (v1)`;

async function goToLanding(page: Page) {
  await page.goto("/application");
  await expect(page).toHaveTitle(/AI Form Assistant/);
}

/** Self-provisions the English-only predefined form this suite needs,
 * directly via the public forms API — no external fixture-loading step
 * required (unlike guided-flow.spec.ts's pre-existing dependency on a
 * separately seeded "Basic Registration" fixture). A single English static
 * translation and no question_key is exactly the "manually selected form
 * with no catalog/multi-language coverage" scenario this fix addresses. */
async function ensureFixtureForm(request: APIRequestContext): Promise<void> {
  const templateRes = await request.post("/api/forms", {
    data: { key: FIXTURE_FORM_KEY, name: FIXTURE_FORM_NAME, description: null },
  });
  const template = await templateRes.json();

  const versionRes = await request.post(`/api/forms/${template.id}/versions`, {
    data: { sourceLanguage: "en", supportedOutputLanguages: ["en"] },
  });
  const version = await versionRes.json();

  await request.post(`/api/form-versions/${version.id}/fields`, {
    data: {
      key: "full_name",
      fieldType: "string",
      required: true,
      position: 1,
      translations: [{ language: "en", label: "What is your full name?" }],
    },
  });

  await request.post(`/api/form-versions/${version.id}/publish`);
}

function createDigitalPdf(name = "select-manually-upload-smoke.pdf"): string {
  const content =
    "BT /F1 18 Tf 100 700 Td (Full Name:) Tj 250 0 Td (Jane Doe) Tj ET";
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
  ];

  let body = "%PDF-1.4\n";
  const offsets: number[] = [0];
  objects.forEach((obj, index) => {
    offsets.push(Buffer.byteLength(body, "latin1"));
    body += `${index + 1} 0 obj\n${obj}\nendobj\n`;
  });

  const xrefOffset = Buffer.byteLength(body, "latin1");
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (let i = 1; i <= objects.length; i++) {
    body += `${String(offsets[i]).padStart(10, "0")} 00000 n \n`;
  }
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;

  const filePath = path.join(os.tmpdir(), name);
  fs.writeFileSync(filePath, Buffer.from(body, "latin1"));
  return filePath;
}

test.describe("Select Manually — language-inconsistency fix (requires backend)", () => {
  test.skip(
    ({ browserName }) => process.env.CI !== "true" && browserName === "chromium",
    "Skipped in local dev unless CI=true; requires a live backend with database"
  );

  test.beforeAll(async ({ request }) => {
    await ensureFixtureForm(request);
  });

  test("Scenario A: German user language + English output language shows a translated question for a manually selected English form", async ({
    page,
  }) => {
    await goToLanding(page);

    await page.getByRole("button", { name: "Deutsch" }).click();
    await page.getByRole("button", { name: /Manuell auswählen/i }).click();

    const formSelect = page.locator("#form-select");
    await expect(formSelect).toBeVisible();
    await formSelect.selectOption({ label: FIXTURE_FORM_OPTION_LABEL });

    const outputSelect = page.locator("#output-select");
    await expect(outputSelect).toBeVisible();
    await outputSelect.selectOption("en");

    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /Unterstützte Sitzung starten/i }).click();

    await page.waitForURL(/\/application\/session\/[a-f0-9-]+/, { timeout: 15000 });
    await page.waitForSelector("form");

    const heading = await page.getByRole("heading", { level: 2 }).textContent();
    expect(heading?.trim()).not.toEqual("What is your full name?");
    expect(heading?.trim().length).toBeGreaterThan(0);
  });

  test("Scenario B: Arabic user language shows a translated question and keeps dir=rtl active", async ({
    page,
  }) => {
    await goToLanding(page);

    await page.getByRole("button", { name: "العربية" }).click();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    await page.getByRole("button", { name: /اختيار يدوي/i }).click();

    const formSelect = page.locator("#form-select");
    await expect(formSelect).toBeVisible();
    await formSelect.selectOption({ label: FIXTURE_FORM_OPTION_LABEL });

    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /بدء الجلسة المساعدة/i }).click();

    await page.waitForURL(/\/application\/session\/[a-f0-9-]+/, { timeout: 15000 });
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    await page.waitForSelector("form");
    const heading = await page.getByRole("heading", { level: 2 }).textContent();
    expect(heading?.trim()).not.toEqual("What is your full name?");
    expect(heading?.trim().length).toBeGreaterThan(0);

    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  });

  test("Scenario C: Upload Form flow is unaffected by the Select Manually fix", async ({
    page,
  }) => {
    await goToLanding(page);

    const pdf = createDigitalPdf();
    await page.locator("input[type='file']").setInputFiles(pdf);
    await expect(page.getByText("select-manually-upload-smoke.pdf")).toBeVisible();

    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /Upload and Analyze/i }).click();

    // Phase 13: the Upload Form flow now processes automatically straight
    // to the guided session — this just confirms it still works end to end
    // and wasn't broken by the Select Manually i18n fix.
    await page.waitForURL(/\/application\/session\/[a-f0-9-]+$/, { timeout: 20000 });

    fs.unlinkSync(pdf);
  });
});
