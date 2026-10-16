import { expect, type Page, test } from "@playwright/test";

import { specTag } from "../tests/spec-tag";

const REQ = specTag("delivery-pipeline", "The demo runs end to end against recorded responses");

// Each step is saved as a frame; scripts/make_demo_gif.py turns them into the README's GIF.
const frame = (page: Page, name: string) =>
  page.screenshot({ path: `test-results/demo-frames/${name}.png` });

async function sendSample(page: Page, title: string) {
  await page.goto("/");
  await page.getByText(title, { exact: true }).click();
  await page.getByRole("button", { name: "Send and watch it run" }).click();
  await page.waitForURL(/\/requests\/[0-9a-f-]{36}$/);
}

test(`${REQ} the clean sample runs live to sent`, async ({ page }) => {
  await page.goto("/");
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

const TOOLTIPS = specTag("run-dashboard", "Path steps explain themselves");

test(`${TOOLTIPS} hovering or focusing a step explains it and what it found`, async ({ page }) => {
  await sendSample(page, "Clean boarding request");
  await expect(page.getByText("The checks passed it, so it went out without a person.")).toBeVisible();
  const tooltip = page.getByRole("tooltip");

  await page.getByRole("button", { name: "Compliance: Done" }).hover();
  await expect(tooltip).toContainText("Code checks every required vaccine against the stay.");
  await expect(tooltip).toContainText("Every required vaccine covers the stay");

  await page.getByRole("button", { name: "Staff review: Not needed" }).hover();
  await expect(tooltip).toContainText("Not needed: nothing was flagged.");
  await frame(page, "03b-step-tooltip");

  await page.mouse.move(0, 0);
  await expect(tooltip).toBeHidden();
  const intake = page.getByRole("button", { name: "Intake: Done" });
  await intake.focus();
  await expect(tooltip).toContainText("Read boarding for Biscuit");
  await expect(intake).toHaveAccessibleDescription(/Read boarding for Biscuit/);
  await page.keyboard.press("Escape");
  await expect(tooltip).toBeHidden();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Choose a step above or a bar in the timeline.")).toBeHidden(); // the inspector opened
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

  await expect(page.getByRole("status")).toHaveText("Sent the reply for Pepper.");
  await expect(card).toBeHidden(); // decided, so it leaves the queue
  await frame(page, "06-approved");
});

const TRY = specTag("run-dashboard", "Every Try preview opens with a summary");

test(`${TRY} the page opens on a made-up request`, async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("button", { name: /Make one up/ })).toHaveClass(/ring-ink/);
  await expect(page.locator("p.font-display.text-xl")).toContainText(/, (boarding|daycare|grooming), /);
  await expect(page.getByRole("img", { name: /^Vaccine certificate attached to the request for / })).toBeVisible();
});

test(`${TRY} a sample's preview opens with its summary`, async ({ page }) => {
  await page.goto("/");
  await page.getByText("Clean boarding request", { exact: true }).click();

  await expect(page.locator("p.font-display.text-xl")).toHaveText("Biscuit, boarding, Mar 24–27, 2027");
  await expect(page.getByText(/^From Avery Lindqvist\. Beagle, 24 lb\. Every vaccine on the card is current for the whole stay\.$/)).toBeVisible();
});
