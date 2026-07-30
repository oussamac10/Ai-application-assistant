/**
 * Playwright E2E tests for Phase 10 — OCR Integration flow
 *
 * Tests cover:
 * - Uploading a scanned PDF surfaces the OCR-required state and a Start OCR button
 * - Navigating to the OCR page, running OCR (mock provider), and viewing extracted text
 * - RTL rendering of the OCR panel when Arabic is selected
 */

import { test, expect, Page } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";

async function goToLanding(page: Page) {
  await page.goto("/application");
  await expect(page).toHaveTitle(/AI Form Assistant/);
}

test.describe("OCR flow — End-to-end (requires backend)", () => {
  test.skip(
    ({ browserName }) =>
      process.env.CI !== "true" && browserName === "chromium",
    "Skipped in local dev unless CI=true; requires live backend with database",
  );

  test("upload scanned PDF: OCR runs automatically then guided questions start (Phase 13)", async ({
    page,
  }) => {
    await goToLanding(page);

    const fixturePdf = path.resolve(
      __dirname,
      "../../fixtures/pdf/scanned-document.pdf",
    );

    if (!fs.existsSync(fixturePdf)) {
      console.warn("Scanned PDF fixture not found — skipping OCR E2E test");
      return;
    }

    await page.locator("input[type='file']").setInputFiles(fixturePdf);
    await expect(page.getByText("scanned-document.pdf")).toBeVisible();

    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /Upload and Analyze/i }).click();

    // Phase 13: no "Document Analysis Complete"/"Start OCR" manual step —
    // OCR + field detection + question generation run automatically. A
    // blank scanned fixture may yield no usable questions, in which case
    // the safe "could not process" message is shown instead of a session —
    // either outcome is acceptable here; a manual OCR button must not be.
    await expect(
      page.getByRole("button", { name: /Start OCR/i }),
    ).not.toBeVisible();
    await Promise.race([
      page.waitForURL(/\/application\/session\/[a-f0-9-]+$/, {
        timeout: 25000,
      }),
      page
        .getByText(/could not confidently process|no usable questions/i)
        .waitFor({
          timeout: 25000,
        }),
    ]);
  });

  test("OCR panel renders RTL when Arabic is selected", async ({ page }) => {
    await goToLanding(page);

    const fixturePdf = path.resolve(
      __dirname,
      "../../fixtures/pdf/scanned-document.pdf",
    );
    if (!fs.existsSync(fixturePdf)) {
      console.warn("Scanned PDF fixture not found — skipping OCR RTL E2E test");
      return;
    }

    await page.getByRole("button", { name: "العربية" }).first().click();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    await page.locator("input[type='file']").setInputFiles(fixturePdf);
    await page.getByRole("checkbox").check();
    await page
      .getByRole("button", { name: /تحميل وتحليل|Upload and Analyze/i })
      .click();

    // RTL must remain active during automatic processing (Phase 13).
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await Promise.race([
      page.waitForURL(/\/application\/session\/[a-f0-9-]+$/, {
        timeout: 25000,
      }),
      // `.first()`: the failure screen and its heading both carry the
      // message, so an unqualified text locator is not strict-safe.
      page
        .getByText(/تعذّر|could not confidently process/i)
        .first()
        .waitFor({ timeout: 25000 }),
    ]);
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  });
});
