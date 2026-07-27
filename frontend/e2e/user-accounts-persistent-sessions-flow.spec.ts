import { test, expect } from "@playwright/test";

function uniqueEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}@example.com`;
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

    // 2. Start a new guided session while authenticated (select manually)
    await page.goto("/application");
    await page.getByRole("button", { name: "Select Manually" }).click();
    const formSelect = page.locator("#form-select");
    await expect(formSelect).toBeVisible();
    await formSelect.selectOption({ label: "Basic Registration (v1)" });
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: "Start Assisted Session" }).click();
    await page.waitForURL(/\/application\/session\/[a-f0-9-]+/);

    // 3. It should already be owned by the account (no claim banner) and
    // show up in My Applications immediately.
    await expect(page.getByText("Save this application?")).not.toBeVisible();
    await page.goto("/applications");
    await expect(page.getByRole("heading", { name: "Basic Registration" })).toBeVisible();

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
    // 1. Start an anonymous guided session (select manually), not logged in.
    await page.goto("/application");
    await page.getByRole("button", { name: "Select Manually" }).click();
    const formSelect = page.locator("#form-select");
    await expect(formSelect).toBeVisible();
    await formSelect.selectOption({ label: "Basic Registration (v1)" });
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: "Start Assisted Session" }).click();
    await page.waitForURL(/\/application\/session\/([a-f0-9-]+)$/);
    const sessionUrl = page.url();
    const sessionId = sessionUrl.split("/").pop() as string;

    // 2. The claim prompt should appear since we're anonymous.
    await expect(page.getByText("Save this application?")).toBeVisible();
    await page.getByRole("link", { name: "Log in to save" }).click();

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

    // 4. Go back to the anonymous session and claim it now that we're logged in.
    await page.goto(`/application/session/${sessionId}`);
    await expect(page.getByText("Save this application?")).toBeVisible();
    await page.getByRole("button", { name: "Save to my account" }).click();
    await expect(page.getByText("Saved to your account.")).toBeVisible();

    // 5. It now appears in My Applications and is resumable there.
    await page.goto("/applications");
    await expect(page.getByRole("heading", { name: "Basic Registration" })).toBeVisible();
    await page.getByRole("button", { name: "Resume" }).click();
    await page.waitForURL(new RegExp(`/application/session/${sessionId}`));
  });
});
