import { test, expect, Page } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";

function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}@example.com`;
}

function createSamplePdf(name: string): string {
  const content =
    "BT /F1 18 Tf 100 700 Td (Full Name:) Tj 250 0 Td (_____________) Tj ET";
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

async function startUploadedSession(page: Page, filename: string): Promise<string> {
  const pdf = createSamplePdf(filename);
  await page.goto("/application", { waitUntil: "networkidle" });
  await page.locator("input[type='file']").setInputFiles(pdf);
  const checkbox = page.getByRole("checkbox");
  await checkbox.waitFor({ state: "visible" });
  await checkbox.check();
  await page.getByRole("button", { name: /Upload and Analyze/i }).click();
  await page.waitForURL(/\/application\/session\/([a-f0-9-]+)$/, {
    timeout: 60_000,
  });
  return page.url().split("/").pop() as string;
}

test.describe("Phase 12 - User accounts and persistent sessions", () => {
  test("register, start a session while logged in, then resume/rename/delete from My Applications", async ({
    page,
  }) => {
    const email = uniqueEmail("owner");

    // 1. Register a new account
    await page.goto("/register");
    await page.getByLabel("Email address").fill(email);
    await page.locator("#register-password").fill("correct-horse-battery");
    await page.locator("#register-password-confirmation").fill("correct-horse-battery");
    await page.getByRole("button", { name: "Create Account" }).click();

    await page.waitForURL(/\/applications$/);
    await expect(page.getByText("You have no saved applications yet.")).toBeVisible();

    // 2. Start a new guided session while authenticated via PDF upload
    await startUploadedSession(page, "account-owned-form.pdf");

    // 3. It should already be owned by the account (no claim banner) and
    // show up in My Applications immediately.
    await expect(page.getByText("Save progress to resume later")).not.toBeVisible();
    await page.goto("/applications");
    await expect(page.getByRole("button", { name: "Rename" })).toBeVisible();

    // 4. Rename it
    await page.getByRole("button", { name: "Rename" }).click();
    const titleInput = page.locator("input[type=text]").first();
    await titleInput.fill("My Renamed Application");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("My Renamed Application")).toBeVisible();

    // 5. Resume it
    await page.getByRole("button", { name: "Resume" }).click();
    await page.waitForURL(/\/application\/session\/[a-f0-9-]+/);
    await expect(page.getByRole("heading", { level: 2 })).toBeVisible();

    // 6. Delete it
    await page.goto("/applications");
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Delete" }).click();
    await expect(page.getByText("You have no saved applications yet.")).toBeVisible();
  });

  test("claims an anonymous session into an account and it becomes resumable from My Applications", async ({
    page,
  }) => {
    // 1. Start an anonymous guided session via upload, not logged in.
    const sessionId = await startUploadedSession(page, "anonymous-claim-form.pdf");

    // 2. The claim prompt should appear since we're anonymous.
    await expect(page.getByText("Save progress to resume later")).toBeVisible();
    await page.getByRole("link", { name: "Log in", exact: true }).click();

    // 3. Register from the login page's link, ending back on /applications.
    await page.waitForURL(/\/login$/);
    await page.getByText("Create one").click();
    await page.waitForURL(/\/register$/);
    const email = uniqueEmail("claimer");
    await page.getByLabel("Email address").fill(email);
    await page.locator("#register-password").fill("correct-horse-battery");
    await page.locator("#register-password-confirmation").fill("correct-horse-battery");
    await page.getByRole("button", { name: "Create Account" }).click();
    await page.waitForURL(/\/applications$/);

    // 4. Go back to the anonymous session; being logged in auto-claims it.
    await page.goto(`/application/session/${sessionId}`);
    await expect(page.getByText("Saved to your account.")).toBeVisible();

    // 5. It now appears in My Applications and is resumable there.
    await page.goto("/applications");
    await expect(page.getByRole("button", { name: "Resume" })).toBeVisible();
    await page.getByRole("button", { name: "Resume" }).click();
    await page.waitForURL(new RegExp(`/application/session/${sessionId}`));
  });
});
