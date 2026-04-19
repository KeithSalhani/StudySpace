import { expect, test } from "playwright/test";

import { installMockStudySpaceApi } from "./support/mockApi";


test("sends a chat question against selected documents", async ({ page }) => {
  const state = await installMockStudySpaceApi(page, {
    authenticated: true,
    user: { username: "ada" },
    documents: [
      { filename: "security-notes.pdf", tag: "Security" },
      { filename: "week-2.pdf", tag: "Security" },
    ],
    tags: ["Security"],
  });

  await page.goto("/");

  const composer = page.getByRole("textbox", {
    name: "Ask a question about your study material",
  });
  await expect(composer).toBeVisible();

  await composer.fill("Summarize the password storage guidance.");
  await page.getByRole("button", { name: "Send question" }).click();

  await expect(
    page.getByText("Grounded answer for: Summarize the password storage guidance.")
  ).toBeVisible();
  await expect(page.getByText("Search breakdown")).toBeVisible();
  await expect(page.getByText("Focused search").first()).toBeVisible();

  expect(state.chatRequests).toHaveLength(1);
  expect(state.chatRequests[0].selected_files).toEqual([
    "security-notes.pdf",
    "week-2.pdf",
  ]);
});
