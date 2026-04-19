import { expect, test } from "playwright/test";

import { installMockStudySpaceApi } from "./support/mockApi";


test("signs in and logs out", async ({ page }) => {
  await installMockStudySpaceApi(page);

  await page.goto("/#login");

  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await page.getByPlaceholder("your-name").fill("ada");
  await page.getByPlaceholder("At least 8 characters").fill("password123");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByText("@ada")).toBeVisible();
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();

  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
});
