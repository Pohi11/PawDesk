import { expect, type Page, test } from "@playwright/test";

import { specTag } from "../tests/spec-tag";

const REQ = specTag("delivery-pipeline", "The demo runs end to end against recorded responses");

// Each step is saved as a frame; scripts/make_demo_gif.py turns them into the README's GIF.
const frame = (page: Page, name: string) =>
  page.screenshot({ path: `test-results/demo-frames/${name}.png` });

async function submitSample(page: Page, title: string) {
  await page.goto("/demo");
  await page.getByRole("button", { name: new RegExp(title) }).click();
  await page.getByRole("button", { name: "Submit and watch the run" }).click();
  await page.waitForURL(/\/requests\/[0-9a-f-]{36}$/);
}

test(`${REQ} the clean sample runs live to sent`, async ({ page }) => {
  await page.goto("/demo");
  await frame(page, "01-demo");

  await submitSample(page, "Clean boarding request");

  await expect(page.getByRole("heading", { level: 1 })).toContainText("Biscuit");
  await expect(page.getByText("sent", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Every check passed.")).toBeVisible();
  await frame(page, "02-clean-sent");

  await page.getByRole("button", { name: /intake\.extract/ }).click();
  await expect(page.getByText("deepseek/deepseek-v4.1-flash").first()).toBeVisible();
  await frame(page, "03-inspector");
});

test(`${REQ} the injection sample waits for review and is approved to sent`, async ({ page }) => {
  await submitSample(page, "Prompt injection attempt");

  await expect(page.getByText("needs review", { exact: true }).first()).toBeVisible();
  await frame(page, "04-injection-flagged");

  await page.goto("/reviews");
  const card = page.locator("article").filter({ hasText: "instruction-like text" });
  await expect(card).toBeVisible();
  await frame(page, "05-review-queue");
  await card.getByPlaceholder("e.g. Dana").fill("Dana");
  await card.getByRole("button", { name: "Approve", exact: true }).click();

  await expect(card.getByText("Done: the request is now sent.")).toBeVisible();
  await frame(page, "06-approved");
});
