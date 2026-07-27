/**
 * Playwright E2E tests for Phase 11 — Dynamic Field Detection flow
 *
 * Tests cover:
 * - Uploading an unmatched digital PDF surfaces the dynamic-field-detection
 *   state and a Detect Fields button
 * - Running detection, reviewing candidates, confirming and rejecting fields
 * - Creating questions from confirmed fields starts a real guided session
 * - The document ownership token never appears in the URL
 */

import { test, expect, Page } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";

async function goToLanding(page: Page) {
  await page.goto("/application");
  await expect(page).toHaveTitle(/AI Form Assistant/);
}

/** Builds a minimal but valid single-page PDF containing real drawn text,
 * so Phase 9 analysis classifies it as a digital_pdf (native text, no
 * images, no AcroForm) rather than unknown_pdf. The label ends in a colon
 * so LocalFieldDetectionProvider's colon-line heuristic actually detects a
 * candidate field (this test exercises the real "local" provider, not the
 * mock one — see FIELD_DETECTION_PROVIDER in docker-compose.yml). */
function createDigitalPdf(name = "unmatched-digital.pdf"): string {
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

/** Builds a minimal valid PDF with a text field ("Full Name:") and a
 * checkbox choice group ("Request category" heading followed by three
 * Housing/Education/Medical options, each preceded by a small stroked
 * square drawn with the raw PDF `re`/`S` operators) — mirroring how real
 * forms draw checkbox controls as vector shapes rather than text glyphs.
 * Exercises the real LocalFieldDetectionProvider end-to-end, matching the
 * marker-geometry synthesis in backend/app/field_detection/extraction.py.
 */
function createMultipleChoicePdf(name = "unmatched-multiple-choice.pdf"): string {
  const content = [
    "BT /F1 18 Tf 100 750 Td (Full Name:) Tj 250 0 Td (Jane Doe) Tj ET",
    "BT /F1 12 Tf 100 700 Td (Request category) Tj ET",
    "100 675 12 12 re S",
    "BT /F1 12 Tf 118 677 Td (Housing) Tj ET",
    "260 675 12 12 re S",
    "BT /F1 12 Tf 278 677 Td (Education) Tj ET",
    "420 675 12 12 re S",
    "BT /F1 12 Tf 438 677 Td (Medical) Tj ET",
  ].join("\n");

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

test.describe("Dynamic field detection flow — End-to-end (requires backend)", () => {
  test.skip(
    ({ browserName }) => process.env.CI !== "true" && browserName === "chromium",
    "Skipped in local dev unless CI=true; requires live backend with database"
  );

  test("upload unmatched digital PDF, detect fields, confirm, and start guided questions", async ({
    page,
  }) => {
    await goToLanding(page);

    const unmatchedPdf = createDigitalPdf();
    await page.locator("input[type='file']").setInputFiles(unmatchedPdf);
    await expect(page.getByText("unmatched-digital.pdf")).toBeVisible();

    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /Upload and Analyze/i }).click();

    await expect(page.getByText(/Document Analysis Complete/i)).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByText(/Dynamic Field Detection Available/i)).toBeVisible();

    const detectBtn = page.getByRole("button", { name: /Detect Fields/i });
    await expect(detectBtn).toBeVisible();
    await detectBtn.click();

    await expect(page).toHaveURL(/\/application\/document\/.+\/detect-fields/);
    // Ownership token must never appear in the URL.
    expect(page.url()).not.toMatch(/token/i);

    await expect(page.getByText(/Detect Form Fields/i)).toBeVisible();
    await page.getByRole("button", { name: /^Start Detection$/i }).click();

    await expect(page.getByText(/field\(s\) detected/i)).toBeVisible({ timeout: 15000 });

    const confirmButtons = page.getByRole("button", { name: /^Confirm$/i });
    await confirmButtons.first().click();
    await expect(page.getByText(/1 confirmed/i)).toBeVisible();

    // The generated guided question must correspond to the confirmed
    // detected field's own label, not an unrelated catalog question.
    const detectedLabel = await page.locator("input").first().inputValue();

    const createQuestionsBtn = page.getByRole("button", { name: /Create Questions/i });
    await expect(createQuestionsBtn).toBeEnabled();
    await createQuestionsBtn.click();

    await expect(page).toHaveURL(/\/application\/session\/.+/, { timeout: 15000 });
    expect(page.url()).not.toMatch(/token/i);

    // The guided question label must match the confirmed field's label
    // (mock provider produces one field per page, e.g. "Mock field page 1").
    await expect(page.getByText(detectedLabel, { exact: false })).toBeVisible({
      timeout: 10000,
    });

    // Answer the single generated question and complete the session.
    await page.locator("input[type='text']").fill("Test Value");
    await page.getByRole("button", { name: "Continue" }).click();

    // Confirmation screen — confirm the extracted value.
    await expect(page.getByText("Confirm Extracted Information")).toBeVisible({
      timeout: 10000,
    });
    await page.getByRole("button", { name: "Confirm" }).click();

    // Should land on the summary screen; confirm and finalize.
    await page.waitForURL(/\/application\/session\/.+\/summary/, { timeout: 15000 });
    await page.getByRole("button", { name: "Confirm and Finalize Summary" }).click();

    await page.waitForURL(/\/application\/session\/.+\/complete/, { timeout: 15000 });
    expect(page.url()).not.toMatch(/token/i);

    // Dynamic sessions must never offer PDF export, and must show the safe
    // unsupported-export message instead.
    await expect(page.getByText(/not supported yet/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole("button", { name: "Generate PDF" })).not.toBeVisible();

    // No Basic Registration PDF (or any PDF) should ever be downloaded.
    const download = await page
      .waitForEvent("download", { timeout: 2000 })
      .catch(() => null);
    expect(download).toBeNull();

    fs.unlinkSync(unmatchedPdf);
  });

  test("known supported template bypasses dynamic detection", async ({ page }) => {
    await goToLanding(page);

    const fixturePdf = path.resolve(
      __dirname,
      "../../fixtures/pdf/basic-registration-v1.pdf"
    );
    if (!fs.existsSync(fixturePdf)) {
      console.warn("basic-registration-v1.pdf fixture not found — skipping bypass test");
      return;
    }

    await page.locator("input[type='file']").setInputFiles(fixturePdf);
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /Upload and Analyze/i }).click();

    await expect(page.getByText(/Document Analysis Complete/i)).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByText(/Supported Template Recognized/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /Detect Fields/i })).not.toBeVisible();
  });

  test("dynamically detected multiple_choice question: select options, submit, and advance to the next question", async ({
    page,
  }) => {
    await goToLanding(page);

    const multiChoicePdf = createMultipleChoicePdf();
    await page.locator("input[type='file']").setInputFiles(multiChoicePdf);
    await expect(page.getByText("unmatched-multiple-choice.pdf")).toBeVisible();

    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /Upload and Analyze/i }).click();

    await expect(page.getByText(/Document Analysis Complete/i)).toBeVisible({
      timeout: 15000,
    });
    await page.getByRole("button", { name: /Detect Fields/i }).click();
    await expect(page).toHaveURL(/\/application\/document\/.+\/detect-fields/);

    await expect(page.getByText(/Detect Form Fields/i)).toBeVisible();
    await page.getByRole("button", { name: /^Start Detection$/i }).click();
    await expect(page.getByText(/field\(s\) detected/i)).toBeVisible({ timeout: 15000 });

    // Confirm both detected fields (the text field and the choice group)
    // in one action, mirroring how a real reviewer would proceed.
    await page.getByRole("button", { name: /Confirm all high-confidence fields/i }).click();

    const createQuestionsBtn = page.getByRole("button", { name: /Create Questions/i });
    await expect(createQuestionsBtn).toBeEnabled();
    await createQuestionsBtn.click();

    await page.waitForURL(/\/application\/session\/.+/, { timeout: 15000 });
    expect(page.url()).not.toMatch(/token/i);

    // First guided question — the text field.
    await page.waitForSelector("form");
    await page.locator("input[type='text']").fill("Jane Doe");
    await page.getByRole("button", { name: "continue" }).or(page.getByText("continue")).click();
    await expect(page.getByText("Confirm Extracted Information")).toBeVisible({
      timeout: 10000,
    });
    await page.getByRole("button", { name: "Confirm" }).click();

    // Second guided question — the dynamically detected multiple_choice
    // "Request category" field. Selecting more than one option and
    // submitting must reach the confirm screen, not silently stall.
    await expect(page.getByText("Request category")).toBeVisible({ timeout: 10000 });
    await page.getByLabel("Housing").check();
    await page.getByLabel("Education").check();
    await page.getByRole("button", { name: "Continue" }).click();

    await expect(page.getByText("Confirm Extracted Information")).toBeVisible({
      timeout: 10000,
    });
    await page.getByRole("button", { name: "Confirm" }).click();

    // Both required fields are now confirmed — the session must actually
    // advance (to the summary screen), not get stuck re-serving the same
    // multiple_choice question.
    await page.waitForURL(/\/application\/session\/.+\/summary/, { timeout: 15000 });

    fs.unlinkSync(multiChoicePdf);
  });
});
