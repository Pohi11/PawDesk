import { expect, test } from "@playwright/test";

import { specTag } from "../tests/spec-tag";

const HOME = specTag("run-dashboard", "The home page introduces PawDesk and holds the Try panel");

test(`${HOME} the home page explains PawDesk and shows the Try panel`, async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("PawDesk reads booking requests and drafts the replies.");
  await expect(page.getByRole("heading", { name: "Try a request" })).toBeVisible();
  await expect(page.getByText("Clean boarding request", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Make one up/ })).toBeVisible();
  for (const section of ["How a request moves", "Pages in the dashboard", "About this project", "Built with"]) {
    await expect(page.getByRole("heading", { name: section })).toBeVisible();
  }
});

test(`${HOME} the old Try page address lands on the home page`, async ({ page }) => {
  await page.goto("/demo");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Try a request" })).toBeVisible();
});

test(`${HOME} the navigation's Requests link opens the list`, async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation").getByRole("link", { name: "Requests", exact: true }).click();
  await expect(page).toHaveURL(/\/requests$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/waiting for you/);
});
