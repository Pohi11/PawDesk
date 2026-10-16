import { expect, test } from "@playwright/test";

import { specTag } from "../tests/spec-tag";

const PAGE = specTag("run-dashboard", "The architecture page shows how the system works");

const DIAGRAMS = ["System parts", "Request path", "Request lifecycle", "Step loop", "Model output checks", "Spans of a clean run"];

test(`${PAGE} the navigation's Architecture link opens the page with its six diagrams`, async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation").getByRole("link", { name: "Architecture", exact: true }).click();
  await expect(page).toHaveURL(/\/architecture$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Architecture");
  for (const name of DIAGRAMS) {
    await expect(page.getByRole("img", { name, exact: true })).toBeVisible();
  }
});

test(`${PAGE} each diagram has a description in words`, async ({ page }) => {
  await page.goto("/architecture");
  await expect(page.getByRole("img", { name: "System parts" })).toHaveAccessibleDescription(/proxy.*OpenRouter/);
  await expect(page.getByRole("img", { name: "Request lifecycle" })).toHaveAccessibleDescription(
    /Staff moves a request from needs_review to approved\./,
  );
  for (const name of DIAGRAMS) {
    const description = await page.getByRole("img", { name, exact: true }).getAttribute("aria-describedby");
    await expect(page.locator(`[id="${description}"]`)).not.toBeEmpty();
  }
});

test(`${PAGE} at phone width the page doesn't scroll sideways`, async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/architecture");
  await expect(page.getByRole("img", { name: "Request lifecycle" })).toBeVisible();

  const [pageWidth, viewWidth] = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
  expect(pageWidth).toBeLessThanOrEqual(viewWidth);
  const frame = page.getByRole("region", { name: "Request lifecycle" });
  const [scrollWidth, clientWidth] = await frame.evaluate((el) => [el.scrollWidth, el.clientWidth]);
  expect(scrollWidth).toBeGreaterThan(clientWidth);
});
