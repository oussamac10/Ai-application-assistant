import { test, expect } from "@playwright/test";

test.describe("AI Form Assistant - E2E Guided Form Flow", () => {
  test("complete guided form flow: select languages, privacy, fill fields, confirm, edit back, summary and complete", async ({ page }) => {
    // Listen to browser console and page errors
    page.on("console", (msg) => console.log(`[CONSOLE] ${msg.type()}: ${msg.text()}`));
    page.on("pageerror", (err) => console.log(`[BROWSER ERROR] ${err.stack || err.message}`));

    // 1. Visit landing page
    await page.goto("/application");
    await expect(page).toHaveTitle(/AI Form Assistant/);

    // Verify language switcher updates HTML lang and dir attributes
    // Switch to Arabic
    await page.getByRole("button", { name: "العربية" }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    // Switch back to English
    await page.getByRole("button", { name: "English" }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");

    // Select the "Basic Registration" form if available
    const formSelect = page.locator("#form-select");
    await expect(formSelect).toBeVisible();
    await formSelect.selectOption({ label: "Basic Registration (v1)" });
    
    // Choose output language as German
    const outputSelect = page.locator("#output-select");
    await expect(outputSelect).toBeVisible();
    await outputSelect.selectOption("de");

    // Click privacy notice checkbox (explicit acceptance required)
    const privacyCheckbox = page.getByRole("checkbox");
    await expect(privacyCheckbox).not.toBeChecked();
    
    // Start session button should be disabled
    const startButton = page.getByRole("button", { name: "Start Assisted Session" });
    await expect(startButton).toBeDisabled();

    // Check privacy box to enable button
    await privacyCheckbox.check();
    await expect(startButton).toBeEnabled();

    // Start Session
    await startButton.click();

    // 2. We should be redirected to the active session URL
    await page.waitForURL(/\/application\/session\/[a-f0-9-]+/);
    const sessionUrl = page.url();
    expect(sessionUrl).toContain("/application/session/");

    // Wait for the first field "First Name" (from seed catalog/fixture definition)
    // Field 1: First Name
    await page.waitForSelector("form");
    await expect(page.getByRole("heading", { level: 2 })).toContainText(/What is your first name\?/);
    
    // Type name
    await page.locator("input[type='text']").fill("John");
    await page.getByRole("button", { name: "Continue" }).click();

    // We should see the confirmation screen
    await expect(page.getByText("Confirm Extracted Information")).toBeVisible();
    await expect(page.getByText("John", { exact: true })).toBeVisible();
    
    // Confirm value
    await page.getByRole("button", { name: "Confirm" }).click();

    // Field 2: Last Name
    await page.waitForSelector("form");
    await expect(page.getByRole("heading", { level: 2 })).toContainText(/What is your last name\?/);
    await page.locator("input[type='text']").fill("Doe");
    await page.getByRole("button", { name: "Continue" }).click();
    
    // Confirm value
    await expect(page.getByText("Confirm Extracted Information")).toBeVisible();
    await page.getByRole("button", { name: "Confirm" }).click();

    // Field 3: Date of Birth
    await page.waitForSelector("form");
    await expect(page.getByRole("heading", { level: 2 })).toContainText(/What is your date of birth\?/);
    await page.locator("input[type='date']").fill("1990-05-15");
    await page.getByRole("button", { name: "Continue" }).click();
    
    // Confirm value
    await expect(page.getByText("Confirm Extracted Information")).toBeVisible();
    await page.getByRole("button", { name: "Confirm" }).click();

    // Field 4: Email Address
    await page.waitForSelector("form");
    await expect(page.getByRole("heading", { level: 2 })).toContainText(/What is your email address\?/);
    await page.locator("input[type='email']").fill("john.doe@example.com");
    await page.getByRole("button", { name: "Continue" }).click();
    
    // Confirm value
    await expect(page.getByText("Confirm Extracted Information")).toBeVisible();
    await page.getByRole("button", { name: "Confirm" }).click();

    // Field 5: Country
    await page.waitForSelector("form");
    await expect(page.getByRole("heading", { level: 2 })).toContainText(/What is your country of residence\?/);
    await page.locator("input[type='text']").fill("Germany");
    await page.getByRole("button", { name: "Continue" }).click();
    
    // Confirm value
    await expect(page.getByText("Confirm Extracted Information")).toBeVisible();
    await page.getByRole("button", { name: "Confirm" }).click();

    // Field 6: Marital Status
    await page.waitForSelector("form");
    await expect(page.getByRole("heading", { level: 2 })).toContainText(/What is your marital status\?/);
    // Standard single choice dropdown
    await page.locator("select").selectOption("single");
    await page.getByRole("button", { name: "Continue" }).click();
    
    // Confirm value
    await expect(page.getByText("Confirm Extracted Information")).toBeVisible();
    await page.getByRole("button", { name: "Confirm" }).click();

    // 3. We should be redirected to the summary page since all required fields are complete
    await page.waitForURL(/\/application\/session\/[a-f0-9-]+\/summary/);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Session Summary");

    // Edit field action test (e.g. click edit on first field first_name)
    const firstRow = page.locator("tbody tr").first();
    await expect(firstRow).toContainText("John");
    await firstRow.getByRole("button", { name: "Edit" }).click();

    // We should be returned back to the relevant workflow page for First Name
    await page.waitForURL(/\/application\/session\/[a-f0-9-]+$/);
    await expect(page.getByRole("heading", { level: 2 })).toContainText(/What is your first name\?/);
    
    // Modify value
    const input = page.locator("#field-first_name");
    await expect(input).toHaveValue("John");
    await input.fill("Johnny");
    await page.getByRole("button", { name: "Continue" }).click();
    
    // Confirm
    await expect(page.getByText("Confirm Extracted Information")).toBeVisible();
    await page.getByRole("button", { name: "Confirm" }).click();

    // We should be redirected back to the summary page
    await page.waitForURL(/\/application\/session\/[a-f0-9-]+\/summary/);
    await expect(page.locator("tbody tr").first()).toContainText("Johnny");

    // Click confirm and finalize summary
    await page.getByRole("button", { name: "Confirm and Finalize Summary" }).click();

    // We should be redirected to the complete page
    await page.waitForURL(/\/application\/session\/[a-f0-9-]+\/complete/);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Form Ready for Export");

    // Click Generate PDF
    const generateBtn = page.getByRole("button", { name: "Generate PDF" });
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    // Verify it prepares and then presents Download PDF button
    const downloadBtn = page.getByRole("button", { name: "Download PDF" });
    await expect(downloadBtn).toBeVisible();

    // Intercept download
    const downloadPromise = page.waitForEvent("download");
    await downloadBtn.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain("registration-");

    // Start a new form
    await page.getByRole("button", { name: "Start a New Form" }).click();
    await page.waitForURL(/\/application$/);
  });
});
