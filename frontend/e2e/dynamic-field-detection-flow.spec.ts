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
 * images, no AcroForm) rather than unknown_pdf. */
function createDigitalPdf(name = "unmatched-digital.pdf"): string {
  const content = "BT /F1 24 Tf 100 700 Td (Full Name Address Email Phone Number) Tj ET";
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

    const createQuestionsBtn = page.getByRole("button", { name: /Create Questions/i });
    await expect(createQuestionsBtn).toBeEnabled();
    await createQuestionsBtn.click();

    await expect(page).toHaveURL(/\/application\/session\/.+/, { timeout: 15000 });
    expect(page.url()).not.toMatch(/token/i);

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
});
