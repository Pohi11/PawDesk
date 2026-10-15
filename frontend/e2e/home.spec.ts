import { expect, test } from "@playwright/test";

import { specTag } from "../tests/spec-tag";

const HOME = specTag("run-dashboard", "The home page introduces PawDesk and holds the Try panel");

test(`${HOME} the home page explains PawDesk and shows the Try panel`, async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("PawDesk handles pet care bookings and asks a person when it isn't sure.");
  const example = page.getByRole("figure", { name: "One request from start to finish" });
  await expect(example.getByRole("blockquote")).toContainText("Could Biscuit board with you from March 24 to March 27?");
  await expect(example).toContainText("Every check passed, so PawDesk sent the reply");
  await expect(page.getByRole("heading", { name: "Try a request" })).toBeVisible();
  await expect(page.getByText("Clean boarding request", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Make one up/ })).toBeVisible();
  const agents = page.locator("#agents");
  for (const agent of ["Intake", "Records", "Resolver", "Reply"]) {
    await expect(agents.getByRole("rowheader", { name: new RegExp(`^${agent}`) })).toBeVisible();
  }
  for (const section of ["The agents", "How a request moves", "What the tests hold it to", "Working with an AI assistant", "Skills from the posting"]) {
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
