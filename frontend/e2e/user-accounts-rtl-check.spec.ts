import { test, expect } from "@playwright/test";

test.describe("Phase 12 - RTL preserved on new auth/applications pages", () => {
  test("Arabic locale keeps dir=rtl on login, register, and applications pages", async ({
    page,
  }) => {
    await page.goto("/application");
    await page.getByRole("button", { name: "العربية" }).click();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

    await page.goto("/login");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");

    await page.goto("/register");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  });
});
