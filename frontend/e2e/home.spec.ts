import { expect, test } from "@playwright/test";

import { specTag } from "../tests/spec-tag";

const HOME = specTag("run-dashboard", "The home page introduces PawDesk and holds the Try panel");
const CARD = specTag("run-dashboard", "The worked example shows the attached vaccine card");
const RULES =specTag("run-dashboard", "The home page explains the booking rules");
const HOW = specTag("run-dashboard", "The hero's How it works link opens the booking rules");

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
  for (const section of ["Booking rules", "The agents", "How a request moves", "What the tests hold it to", "Working with an AI assistant", "Skills from the posting"]) {
    await expect(page.getByRole("heading", { name: section })).toBeVisible();
  }
});

test(`${CARD} the worked example shows the attached vaccine card`, async ({ page }) => {
  await page.goto("/");

  const card = page.getByRole("figure", { name: "One request from start to finish" }).getByRole("img", { name: /Biscuit's vaccine card/ });
  await expect(card).toBeVisible();
  await expect(card).toHaveAttribute("src", "/api/demo/samples/clean/certificate.png");
  await expect.poll(() => card.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth)).toBeGreaterThan(0);
});

test(`${HOME} the old Try page address lands on the home page`, async ({ page }) => {
  await page.goto("/demo");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Try a request" })).toBeVisible();
});

test(`${HOW} How it works scrolls to the booking rules`, async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "How it works", exact: true }).click();
  await expect(page).toHaveURL(/#rules$/);
  await expect(page.getByRole("heading", { name: "Booking rules", level: 2 })).toBeInViewport();
});

test(`${HOME} the navigation's Requests link opens the list`, async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation").getByRole("link", { name: "Requests", exact: true }).click();
  await expect(page).toHaveURL(/\/requests$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(/waiting for you/);
});

test(`${RULES} the services, the coverage rule, and kennel sizes are on the page`, async ({ page }) => {
  await page.goto("/");
  const services = page.locator("#rules table");
  const row = (name: string) => services.getByRole("row", { name: new RegExp(`^${name}`) });
  await expect(row("Boarding")).toContainText("at least one night");
  await expect(row("Boarding")).toContainText("A free kennel");
  await expect(row("Daycare")).toContainText("Canine influenza");
  await expect(row("Grooming")).toContainText("None");

  const strip = page.getByRole("figure", { name: "Two vaccines against Biscuit's stay from March 24 to 27" });
  await expect(strip).toContainText("Covers the stay");
  await expect(strip).toContainText("Expires during the stay");
  await expect(page.locator("#rules")).toContainText("20 to under 50 lb");
});
