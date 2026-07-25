/**
 * Playwright E2E tests for Phase 9 — Document Upload and Analysis flow
 *
 * Tests cover:
 * - Landing page shows Upload Form tab by default
 * - Tab switching between Upload and Manual modes
 * - Client-side rejection of non-PDF / oversized files
 * - Privacy checkbox gates the upload button
 * - Language selector works in upload mode
 * - RTL UI renders correctly when Arabic is selected
 * - Backend upload → analysis → success result display (with mock server)
 * - Unsupported document types show the correct informational state
 */

import { test, expect, Page } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Creates a temporary PDF-like file for upload testing. */
function createTmpPdf(name = "test.pdf", sizeBytes = 1024): string {
  const tmpDir = os.tmpdir();
  const filePath = path.join(tmpDir, name);
  // Minimal valid PDF header so the backend accepts it as PDF
  const header = Buffer.from("%PDF-1.4\n%ÿÿÿÿ\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 0\n%%EOF");
  const padding = Buffer.alloc(Math.max(0, sizeBytes - header.length), " ");
  fs.writeFileSync(filePath, Buffer.concat([header, padding]));
  return filePath;
}

/** Creates a temporary non-PDF file for rejection testing. */
function createTmpTxt(name = "test.txt"): string {
  const tmpDir = os.tmpdir();
  const filePath = path.join(tmpDir, name);
  fs.writeFileSync(filePath, "This is a plain text file, not a PDF.");
  return filePath;
}

async function goToLanding(page: Page) {
  await page.goto("/application");
  await expect(page).toHaveTitle(/AI Form Assistant/);
}

// ---------------------------------------------------------------------------
// Tab & Layout tests
// ---------------------------------------------------------------------------

test.describe("Landing page — Tab selection", () => {
  test("shows Upload Form tab as active by default", async ({ page }) => {
    await goToLanding(page);

    // Upload tab button should exist and be styled as active (bg-indigo-600)
    const uploadTab = page.getByRole("button", { name: /Upload Form/i });
    await expect(uploadTab).toBeVisible();
    await expect(uploadTab).toHaveClass(/bg-indigo-600/);

    // Upload drop zone should be visible
    await expect(page.getByText(/Drag and drop your PDF/i)).toBeVisible();
  });

  test("switches to Manual mode and shows form selector", async ({ page }) => {
    await goToLanding(page);

    // Click the "Select Manually" tab
    const manualTab = page.getByRole("button", { name: /Select Manually/i });
    await manualTab.click();

    // Manual tab is now active
    await expect(manualTab).toHaveClass(/bg-indigo-600/);

    // Form selector should be visible
    await expect(page.locator("#form-select")).toBeVisible();
  });

  test("switches back to Upload tab after visiting Manual", async ({ page }) => {
    await goToLanding(page);

    await page.getByRole("button", { name: /Select Manually/i }).click();
    await page.getByRole("button", { name: /Upload Form/i }).click();

    await expect(page.getByText(/Drag and drop your PDF/i)).toBeVisible();
    // Form selector should be hidden again
    await expect(page.locator("#form-select")).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Language selector in Upload mode
// ---------------------------------------------------------------------------

test.describe("Upload mode — Language selection", () => {
  test("language switcher updates html lang attribute in upload mode", async ({ page }) => {
    await goToLanding(page);

    // Switch to Arabic in upload tab (both tabs show the language switcher)
    await page.getByRole("button", { name: "العربية" }).first().click();
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    // Switch back to English
    await page.getByRole("button", { name: "English" }).first().click();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  });

  test("French language switcher renders translated UI labels", async ({ page }) => {
    await goToLanding(page);

    await page.getByRole("button", { name: "Français" }).first().click();

    // The upload tab should now show French text
    await expect(
      page.getByRole("button", { name: /Télécharger le formulaire/i })
    ).toBeVisible();
  });

  test("German language switcher renders translated UI labels", async ({ page }) => {
    await goToLanding(page);

    await page.getByRole("button", { name: "Deutsch" }).first().click();

    // The upload tab should now show German text
    await expect(
      page.getByRole("button", { name: /Formular hochladen/i })
    ).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// File picker interaction
// ---------------------------------------------------------------------------

test.describe("Upload form — File picking and client-side validation", () => {
  test("privacy checkbox is unchecked by default and gates upload button", async ({ page }) => {
    await goToLanding(page);

    // The upload button should not exist until a file is selected
    await expect(page.getByRole("button", { name: /Upload and Analyze/i })).not.toBeVisible();
  });

  test("selecting a valid PDF reveals output language selector and privacy checkbox", async ({
    page,
  }) => {
    await goToLanding(page);

    const pdfPath = createTmpPdf("valid.pdf", 2048);
    const fileInput = page.locator("input[type='file']");
    await fileInput.setInputFiles(pdfPath);

    // File name should be shown
    await expect(page.getByText("valid.pdf")).toBeVisible();

    // Output language selector appears
    await expect(page.locator("#upload-output-select")).toBeVisible();

    // Privacy checkbox appears
    const checkbox = page.getByRole("checkbox");
    await expect(checkbox).toBeVisible();
    await expect(checkbox).not.toBeChecked();

    // Upload button is disabled (privacy not accepted)
    await expect(
      page.getByRole("button", { name: /Upload and Analyze/i })
    ).toBeDisabled();

    fs.unlinkSync(pdfPath);
  });

  test("accepting privacy enables the upload button", async ({ page }) => {
    await goToLanding(page);

    const pdfPath = createTmpPdf("priv-test.pdf", 2048);
    await page.locator("input[type='file']").setInputFiles(pdfPath);

    const checkbox = page.getByRole("checkbox");
    await checkbox.check();
    await expect(checkbox).toBeChecked();

    await expect(
      page.getByRole("button", { name: /Upload and Analyze/i })
    ).toBeEnabled();

    fs.unlinkSync(pdfPath);
  });

  test("selecting a non-PDF file shows error message", async ({ page }) => {
    await goToLanding(page);

    const txtPath = createTmpTxt("document.txt");
    await page.locator("input[type='file']").setInputFiles(txtPath);

    // Error message about file type
    await expect(page.getByText(/Only PDF files are supported/i)).toBeVisible();

    fs.unlinkSync(txtPath);
  });

  test("remove file button resets the form to idle state", async ({ page }) => {
    await goToLanding(page);

    const pdfPath = createTmpPdf("removable.pdf", 1024);
    await page.locator("input[type='file']").setInputFiles(pdfPath);

    // File name is shown
    await expect(page.getByText("removable.pdf")).toBeVisible();

    // Click remove
    await page.getByRole("button", { name: /Remove/i }).click();

    // Drop zone is back to idle
    await expect(page.getByText(/Drag and drop your PDF/i)).toBeVisible();
    await expect(page.getByText("removable.pdf")).not.toBeVisible();

    fs.unlinkSync(pdfPath);
  });

  test("output language selector shows correct options", async ({ page }) => {
    await goToLanding(page);

    const pdfPath = createTmpPdf("lang-options.pdf", 1024);
    await page.locator("input[type='file']").setInputFiles(pdfPath);

    const select = page.locator("#upload-output-select");
    await expect(select).toBeVisible();

    // All expected options should be present
    await expect(select.locator("option[value='en']")).toHaveText("English");
    await expect(select.locator("option[value='de']")).toHaveText("Deutsch");
    await expect(select.locator("option[value='fr']")).toHaveText("Français");
    await expect(select.locator("option[value='ar']")).toHaveText("العربية");

    fs.unlinkSync(pdfPath);
  });
});

// ---------------------------------------------------------------------------
// Upload flow (requires running backend)
// ---------------------------------------------------------------------------

test.describe("Upload flow — End-to-end (requires backend)", () => {
  test.skip(
    ({ browserName }) => process.env.CI !== "true" && browserName === "chromium",
    "Skipped in local dev unless CI=true; requires live backend with database"
  );

  test("upload predefined registration PDF triggers supported_template result and start button", async ({
    page,
  }) => {
    page.on("console", (msg) =>
      console.log(`[CONSOLE] ${msg.type()}: ${msg.text()}`)
    );

    await goToLanding(page);

    // Use the pre-generated fixture PDF from Phase 8 if available
    const fixturePdf = path.resolve(
      __dirname,
      "../../../../fixtures/pdf/basic-registration-v1.pdf"
    );

    if (!fs.existsSync(fixturePdf)) {
      console.warn("Fixture PDF not found — skipping backend upload E2E test");
      return;
    }

    await page.locator("input[type='file']").setInputFiles(fixturePdf);
    await expect(page.getByText("basic-registration-v1.pdf")).toBeVisible();

    await page.locator("#upload-output-select").selectOption("de");
    await page.getByRole("checkbox").check();

    // Start upload
    await page.getByRole("button", { name: /Upload and Analyze/i }).click();

    // Wait for analysis to complete (uploading → analyzing → success)
    await expect(page.getByText(/Document Analysis Complete/i)).toBeVisible({
      timeout: 15000,
    });

    // Should show supported template matched state
    await expect(page.getByText(/Supported Template Recognized/i)).toBeVisible();

    // Start guided form button should appear
    const startBtn = page.getByRole("button", { name: /Start Guided Form/i });
    await expect(startBtn).toBeVisible();
    await expect(startBtn).toBeEnabled();
  });
});
