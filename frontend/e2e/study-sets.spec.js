import { expect, test } from "playwright/test";

import { installMockStudySpaceApi } from "./support/mockApi";


test("generates and displays a saved study set", async ({ page }) => {
  await installMockStudySpaceApi(page, {
    authenticated: true,
    user: { username: "ada" },
    documents: [{ filename: "security-notes.pdf", tag: "Security" }],
    tags: ["Security"],
  });

  await page.goto("/");

  await page.getByLabel("Source document").selectOption("security-notes.pdf");
  await page.getByRole("button", { name: "Flashcards" }).click();
  await page.getByRole("button", { name: "Generate Flashcards" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("Security Flashcards")).toBeVisible();
  await expect(dialog.getByText("What is hashing?")).toBeVisible();
  await expect(dialog.getByText("security-notes.pdf")).toBeVisible();

  await page.getByRole("button", { name: /Flip flashcard 1 of 2/i }).click();
  await expect(page.getByText("A one-way transformation for stored secrets.")).toBeVisible();

  await expect(page.getByText("No saved study sets yet.")).not.toBeVisible();
  await expect(
    page.locator(".saved-study-card").filter({ hasText: "Security Flashcards" })
  ).toBeVisible();
});
