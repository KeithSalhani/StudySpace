import { expect, test } from "playwright/test";

import { installMockStudySpaceApi } from "./support/mockApi";


test("uploads and removes a document", async ({ page }) => {
  await installMockStudySpaceApi(page, {
    authenticated: true,
    user: { username: "ada" },
    documents: [],
    tags: [],
  });

  page.on("dialog", (dialog) => dialog.accept());

  await page.goto("/");

  await expect(page.getByText("No documents yet. Start by dropping a file.")).toBeVisible();
  await page.locator('input[type="file"][multiple]').setInputFiles({
    name: "crypto-notes.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 mock pdf"),
  });

  await expect(page.locator(".document-name", { hasText: "crypto-notes.pdf" })).toBeVisible();
  await page.getByLabel("Delete crypto-notes.pdf").click();
  await expect(page.locator(".document-name", { hasText: "crypto-notes.pdf" })).not.toBeVisible();
  await expect(page.getByText("No documents yet. Start by dropping a file.")).toBeVisible();
});


test("creates and deletes a topic tag from settings", async ({ page }) => {
  await installMockStudySpaceApi(page, {
    authenticated: true,
    user: { username: "ada" },
    tags: ["Security"],
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Settings" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await dialog.getByPlaceholder("Add a topic lens (e.g. AI, CS101)...").fill("Databases");
  await dialog.getByRole("button", { name: "Add" }).click();

  const databasesChip = dialog.locator(".tag-chip").filter({ hasText: "Databases" });
  await expect(databasesChip).toBeVisible();
  await databasesChip.getByRole("button", { name: "Delete Databases" }).click();
  await expect(databasesChip).not.toBeVisible();
});


test("creates and deletes a note", async ({ page }) => {
  await installMockStudySpaceApi(page, {
    authenticated: true,
    user: { username: "ada" },
    notes: [],
  });

  await page.goto("/");

  await page.getByLabel("New note").fill("Revise lecture 4 before Friday");
  await page.getByRole("button", { name: "Save note" }).click();

  await expect(page.getByText("Revise lecture 4 before Friday")).toBeVisible();
  await page.getByRole("button", { name: "Delete" }).click();
  await expect(page.getByText("Revise lecture 4 before Friday")).not.toBeVisible();
});


test("toggles accessibility settings and applies body classes", async ({ page }) => {
  await installMockStudySpaceApi(page, {
    authenticated: true,
    user: { username: "ada" },
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Settings" }).click();

  const dialog = page.getByRole("dialog");
  const highContrastToggle = dialog
    .locator(".settings-toggle")
    .filter({ hasText: "Higher contrast surfaces" })
    .locator('input[type="checkbox"]');
  const enhancedFocusToggle = dialog
    .locator(".settings-toggle")
    .filter({ hasText: "Enhanced focus indicators" })
    .locator('input[type="checkbox"]');

  await highContrastToggle.check();
  await enhancedFocusToggle.check();

  await expect(page.locator("body")).toHaveClass(/a11y-high-contrast/);
  await expect(page.locator("body")).toHaveClass(/a11y-enhanced-focus/);
});


test("opens document metadata from an icon and deletes an entry", async ({ page }) => {
  await installMockStudySpaceApi(page, {
    authenticated: true,
    user: { username: "ada" },
    documents: [{ filename: "crypto-notes.pdf", tag: "Security" }],
    tags: ["Security"],
    metadata: {
      "crypto-notes.pdf": {
        assessments: [
          { item: "Midterm", weight: "40%" },
          { item: "Coursework", weight: "60%" },
        ],
        deadlines: [{ event: "Midterm", date: "2026-05-12" }],
        contacts: [{ name: "Dr. Rao", role: "Lecturer", email: "rao@example.edu" }],
      },
    },
  });

  await page.goto("/");

  await page.getByLabel("View metadata for crypto-notes.pdf").click();
  await expect(page.getByText("Midterm • 40%")).toBeVisible();
  await expect(page.getByText("Dr. Rao (Lecturer) • rao@example.edu")).toBeVisible();

  await page.locator(".metadata-section").filter({ hasText: "Assessments" }).getByRole("button", { name: "Delete" }).first().click();

  await expect(page.getByText("Midterm • 40%")).not.toBeVisible();
  await expect(page.getByText("Coursework • 60%")).toBeVisible();
});
