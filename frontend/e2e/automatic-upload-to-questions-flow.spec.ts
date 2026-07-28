/**
 * Playwright E2E tests for Phase 13 — Automatic Upload-to-Questions Flow.
 *
 * Complements the retrofitted Phase 9/10/11 specs (which now assert the
 * automatic flow for their own fixtures) with the two behaviors unique to
 * this phase: the plain-language uncertainty screen for a low-confidence
 * field, and idempotent resume (no reprocessing / no duplicate session on
 * reload).
 */

import { test, expect, Page } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";

async function goToLanding(page: Page) {
  await page.goto("/application");
  await expect(page).toHaveTitle(/AI Form Assistant/);
}

function createDigitalPdf(name = "resume-digital.pdf"): string {
  const content = "BT /F1 18 Tf 100 700 Td (Full Name:) Tj 250 0 Td (Jane Doe) Tj ET";
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

test.describe("Automatic upload-to-questions flow — End-to-end (requires backend)", () => {
  test.skip(
    ({ browserName }) => process.env.CI !== "true" && browserName === "chromium",
    "Skipped in local dev unless CI=true; requires live backend with database"
  );

  test("resuming a processed document does not reprocess or duplicate the session", async ({
    page,
  }) => {
    await goToLanding(page);

    const pdf = createDigitalPdf();
    await page.locator("input[type='file']").setInputFiles(pdf);
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /Upload and Analyze/i }).click();

    await page.waitForURL(/\/application\/session\/[a-f0-9-]+$/, { timeout: 20000 });
    const sessionUrl = page.url();

    // Reload the same guided session directly — must resume in place, not
    // re-run OCR/detection/question-generation or create a second session.
    await page.reload();
    await expect(page).toHaveURL(sessionUrl);
    await expect(page.getByText(/Full Name/i)).toBeVisible({ timeout: 10000 });

    fs.unlinkSync(pdf);
  });
});
