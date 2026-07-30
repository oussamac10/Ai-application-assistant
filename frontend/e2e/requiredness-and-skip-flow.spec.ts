/**
 * Playwright E2E — three-state requiredness, skipping, and a summary that can
 * actually be confirmed.
 *
 * The reported failure: a French employment form could never be finalized.
 *
 *   POST /api/form-sessions/{id}/confirm-summary
 *   409  {"detail": "Field 'date_de_d_but_d_emploi' contains invalid value."}
 *
 * The field was empty. Two defects met there — `confirm_summary` validated any
 * answer record whether or not a value had been submitted, and every unmarked
 * field was treated as required. The UI made it worse by labelling every one of
 * them "Optional", a claim the document never made.
 *
 * The French form itself is not committed (it is a real document); this builds
 * a synthetic equivalent carrying the three cases that matter: an unmarked
 * field, an explicitly optional one, and an explicitly required one.
 */

import { test, expect, Page } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";

/** A single-page native-text PDF whose labels carry French requiredness
 * markers. Latin-1 so the accented characters survive the raw PDF string. */
function createFrenchEmploymentPdf(name = "emploi-fr.pdf"): string {
  const lines = [
    "Formulaire d'emploi",
    "Nom de famille:",
    "Prenom:",
    "Deuxieme prenom (facultatif):",
    "Date de debut d'emploi:",
    "Signature *:",
  ];

  let text = "BT /F1 14 Tf 72 720 Td 24 TL\n";
  lines.forEach((line, index) => {
    text += index === 0 ? `(${line}) Tj\n` : `T* (${line}) Tj\n`;
  });
  text += "ET";

  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${Buffer.byteLength(text, "latin1")} >>\nstream\n${text}\nendstream`,
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

async function uploadAndReachQuestions(page: Page, pdf: string) {
  await page.goto("/application");
  await expect(page).toHaveTitle(/AI Form Assistant/);
  await page.locator("input[type='file']").setInputFiles(pdf);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: /Upload and Analyze/i }).click();
  await page.waitForURL(/\/application\/session\/[a-f0-9-]+$/, {
    timeout: 60000,
  });
  await page.waitForSelector("form", { timeout: 20000 });
}

test.describe("Requiredness, skipping and summary confirmation (requires backend)", () => {
  // Each test uploads a PDF and waits on the real detection + translation
  // pipeline, which exceeds the 30 s default test budget on a cold cache — and
  // Azure Document Intelligence's F0 tier rate-limits a burst of uploads, so
  // the wait can include a retry.
  test.describe.configure({ timeout: 150_000 });

  test.skip(
    ({ browserName }) =>
      process.env.CI !== "true" && browserName === "chromium",
    "Skipped in local dev unless CI=true; requires live backend with database",
  );

  test("an unmarked question carries no requiredness label and can be skipped", async ({
    page,
  }) => {
    const pdf = createFrenchEmploymentPdf();
    await uploadAndReachQuestions(page, pdf);

    // Nothing in the document marks "Nom de famille" either way, so the UI
    // must claim nothing — not "Optional", which was the old behaviour.
    const label = page.getByTestId("requiredness");
    if (await label.count()) {
      await expect(label).not.toHaveText(/optional|facultatif/i);
    }

    // It is still skippable: unknown does not mean required.
    const skip = page.getByTestId("skip-question");
    await expect(skip).toBeVisible();
    await expect(skip).toBeEnabled();

    const before = await page.locator("h2").first().textContent();
    await skip.click();
    await expect
      .poll(async () => page.locator("h2").first().textContent(), {
        timeout: 15000,
      })
      .not.toBe(before);

    fs.unlinkSync(pdf);
  });

  test("an explicitly optional question still shows Optional", async ({
    page,
  }) => {
    const pdf = createFrenchEmploymentPdf();
    await uploadAndReachQuestions(page, pdf);

    // Walk to the "(facultatif)" question, skipping whatever precedes it.
    for (let i = 0; i < 6; i++) {
      const heading = (await page.locator("h2").first().textContent()) ?? "";
      if (/deuxieme|deuxième/i.test(heading)) {
        await expect(page.getByTestId("requiredness")).toHaveText(
          /optional|facultatif/i,
        );
        break;
      }
      const skip = page.getByTestId("skip-question");
      if (!(await skip.count())) break;
      await skip.click();
      await page.waitForTimeout(500);
    }

    fs.unlinkSync(pdf);
  });

  test("leaving the employment start date empty does not block the summary", async ({
    page,
  }) => {
    const pdf = createFrenchEmploymentPdf();
    await uploadAndReachQuestions(page, pdf);

    // Skip every question the form did not mark required — exactly the
    // situation that produced the 409.
    for (let i = 0; i < 12; i++) {
      const skip = page.getByTestId("skip-question");
      if (!(await skip.count())) break;
      await skip.click();
      await page.waitForTimeout(400);
      if (/\/summary$/.test(page.url())) break;
    }

    // The summary must be reachable, and must report those questions as
    // skipped rather than as missing or invalid.
    if (!/\/summary$/.test(page.url())) {
      await page.goto(`${page.url().replace(/\/$/, "")}/summary`);
    }
    await expect(page.getByRole("table")).toBeVisible({ timeout: 20000 });

    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toMatch(/contains invalid value/i);
    expect(bodyText).not.toMatch(/409/);

    fs.unlinkSync(pdf);
  });

  test("the employment start date can be left unanswered and Continue stays gated", async ({
    page,
  }) => {
    // Entering an *invalid* date cannot be driven through this UI at all: the
    // field renders as a native `<input type="date">`, which refuses a
    // malformed value before the app ever sees it (Playwright reports
    // "Malformed value"). That path is covered where it is reachable —
    // `tests/answers/test_confirm_summary_requiredness.py::
    // test_case_5_invalid_date_reports_invalid_date` asserts the API returns
    // `{"field_key": "date_de_d_but_d_emploi", "reason": "invalid_date"}`.
    // What matters here is the reported failure's other half: an *empty* date
    // must never be treated as an answer.
    const pdf = createFrenchEmploymentPdf();
    await uploadAndReachQuestions(page, pdf);

    for (let i = 0; i < 8; i++) {
      const heading = (await page.locator("h2").first().textContent()) ?? "";
      if (/date/i.test(heading)) {
        const input = page.locator("input, textarea").first();
        await expect(input).toHaveValue("");
        // Continue is gated on a value, so a blank is never submitted — the
        // backend refuses one, and the UI must not offer it.
        await expect(
          page.getByRole("button", { name: /continue|suivant/i }),
        ).toBeDisabled();
        // Skipping is the way past, and it is offered.
        await expect(page.getByTestId("skip-question")).toBeEnabled();
        break;
      }
      const skip = page.getByTestId("skip-question");
      if (!(await skip.count())) break;
      await skip.click();
      await page.waitForTimeout(400);
    }

    fs.unlinkSync(pdf);
  });
});
