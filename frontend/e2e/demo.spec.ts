import { expect, type Page, test } from "@playwright/test";

import { specTag } from "../tests/spec-tag";

const REQ = specTag("delivery-pipeline", "The demo runs end to end against recorded responses");

// Each step is saved as a frame; scripts/make_demo_gif.py turns them into the README's GIF.
const frame = (page: Page, name: string) =>
  page.screenshot({ path: `test-results/demo-frames/${name}.png` });

async function sendSample(page: Page, title: string) {
  await page.goto("/demo");
  await page.getByText(title, { exact: true }).click();
  await page.getByRole("button", { name: "Send and watch it run" }).click();
  await page.waitForURL(/\/requests\/[0-9a-f-]{36}$/);
}

test(`${REQ} the clean sample runs live to sent`, async ({ page }) => {
  await page.goto("/demo");
  await frame(page, "01-demo");

  await sendSample(page, "Clean boarding request");

  await expect(page.getByRole("heading", { level: 1 })).toContainText("Biscuit");
  await expect(page.getByText("The checks passed it, so it went out without a person.")).toBeVisible();
  await expect(page.getByText("Every check passed.")).toBeVisible();
  await frame(page, "02-clean-sent");

  await page.getByRole("button", { name: /intake\.extract/ }).click();
  await expect(page.getByText("deepseek/deepseek-v4.1-flash").first()).toBeVisible();
  await frame(page, "03-inspector");
});

test(`${REQ} the injection sample waits for review and is approved to sent`, async ({ page }) => {
  await sendSample(page, "Prompt injection attempt");

  await expect(page.getByText("Waiting for you: message contains instruction-like text.")).toBeVisible();
  await frame(page, "04-injection-flagged");

  await page.goto("/reviews");
  const card = page.locator("article").filter({ hasText: "instruction-like text" });
  await expect(card).toBeVisible();
  await page.getByPlaceholder("Your name").fill("Dana");
  await frame(page, "05-review-queue");
  await card.getByRole("button", { name: "Send reply", exact: true }).click();

  await expect(page.getByRole("status")).toHaveText("Sent the reply for Biscuit.");
  await expect(card).toBeHidden(); // decided, so it leaves the queue
  await frame(page, "06-approved");
});
