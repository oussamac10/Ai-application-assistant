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
    ({ browserName }) => process.env.CI !== "true" && browserName === "chromium",
    "Skipped in local dev unless CI=true; requires live backend with database"
  );

  test("upload scanned PDF shows OCR-required state with Start OCR button", async ({
    page,
  }) => {
    await goToLanding(page);

    const fixturePdf = path.resolve(
      __dirname,
      "../../fixtures/pdf/scanned-document.pdf"
    );

    if (!fs.existsSync(fixturePdf)) {
      console.warn("Scanned PDF fixture not found — skipping OCR E2E test");
      return;
    }

    await page.locator("input[type='file']").setInputFiles(fixturePdf);
    await expect(page.getByText("scanned-document.pdf")).toBeVisible();

    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /Upload and Analyze/i }).click();

    await expect(page.getByText(/Document Analysis Complete/i)).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByText(/OCR Recognition Needed/i)).toBeVisible();

    const startOcrBtn = page.getByRole("button", { name: /Start OCR/i });
    await expect(startOcrBtn).toBeVisible();
    await startOcrBtn.click();

    await expect(page).toHaveURL(/\/application\/document\/.+\/ocr/);
    await expect(page.getByText(/Extract Text with OCR/i)).toBeVisible();

    await page.getByRole("button", { name: /^Start OCR$/i }).click();

    await expect(page.getByText(/OCR Result/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/Mock OCR page 1/i)).toBeVisible();
  });

  test("OCR panel renders RTL when Arabic is selected", async ({ page }) => {
    await goToLanding(page);

    const fixturePdf = path.resolve(
      __dirname,
      "../../fixtures/pdf/scanned-document.pdf"
    );
    if (!fs.existsSync(fixturePdf)) {
      console.warn("Scanned PDF fixture not found — skipping OCR RTL E2E test");
      return;
    }

    await page.getByRole("button", { name: "العربية" }).first().click();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    await page.locator("input[type='file']").setInputFiles(fixturePdf);
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /تحميل وتحليل|Upload and Analyze/i }).click();

    await expect(page.getByText(/OCR Recognition Needed|بدء التعرف الضوئي/i)).toBeVisible({
      timeout: 15000,
    });

    const startOcrBtn = page.getByRole("button", { name: /بدء التعرف الضوئي/i });
    await startOcrBtn.click();

    await expect(page).toHaveURL(/\/application\/document\/.+\/ocr/);
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  });
});
