import { expect, test } from "@playwright/test";

import worked from "../content/worked-example.json";
import { specTag } from "../tests/spec-tag";

const HOME = specTag("run-dashboard", "The home page introduces PawDesk and holds the Try panel");
const CARD = specTag("run-dashboard", "The worked example shows the attached vaccine card");
const RULES = specTag("run-dashboard", "The home page explains the booking rules");
const HOW = specTag("run-dashboard", "The hero's How it works link opens the booking rules");
const OUTCOME = specTag("run-dashboard", "The worked example shows what PawDesk did");
const EXAMPLE = specTag("run-dashboard", "The coverage diagram is a hypothetical example");
const NAV_TRY = specTag("run-dashboard", "The navigation's Try a request link opens the Try panel");
const HYBRID = specTag("run-dashboard", "The home page describes PawDesk as a hybrid workflow");

test(`${HOME} the home page explains PawDesk and shows the Try panel`, async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("PawDesk handles pet care bookings and asks a person when it isn't sure.");
  const example = page.getByRole("figure", { name: "One request from start to finish" });
  await expect(example.getByRole("blockquote")).toContainText("Could Biscuit board with you from March 24 to March 27?");
  await expect(example).toContainText("Example request.");
  await expect(page.getByRole("heading", { name: "Try a request" })).toBeVisible();
  await expect(page.getByText("Clean boarding request", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Make one up/ })).toBeVisible();
  const agents = page.locator("#agents");
  for (const agent of ["Intake", "Records", "Resolver", "Reply"]) {
    await expect(agents.getByRole("rowheader", { name: new RegExp(`^${agent}`) })).toBeVisible();
  }
  for (const section of ["Booking rules", "Model Use", "How a request moves", "What the tests hold it to", "Working with an AI assistant", "Skills across the stack"]) {
    await expect(page.getByRole("heading", { name: section })).toBeVisible();
  }
});

test(`${HYBRID} the introduction calls PawDesk a hybrid workflow`, async ({ page }) => {
  await page.goto("/");

  const intro = page.getByText(/^PawDesk is a /);
  await expect(intro).toContainText("hybrid workflow");
  await expect(intro).toContainText("fixed order");
  await expect(intro).not.toContainText(/multi-agent/i);
});

test(`${CARD} the worked example shows the attached vaccine card`, async ({ page }) => {
  await page.goto("/");

  const card = page.getByRole("figure", { name: "One request from start to finish" }).getByRole("img", { name: /Biscuit's vaccine card/ });
  await expect(card).toBeVisible();
  await expect(card).toHaveAttribute("src", "/api/demo/samples/clean/certificate.png");
  await expect.poll(() => card.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth)).toBeGreaterThan(0);
});

test(`${CARD} the worked example is labeled and its card expands`, async ({ page }) => {
  await page.goto("/");

  const example = page.getByRole("figure", { name: "One request from start to finish" });
  await expect(example.getByText("Example request.", { exact: true })).toBeVisible();

  const card = example.getByRole("img", { name: /Biscuit's vaccine card/ });
  const toggle = example.getByRole("button", { name: "Show the full card" });
  const clipped = (await card.evaluate((img) => img.parentElement!.getBoundingClientRect().height));
  const full = (await card.boundingBox())!.height;
  expect(clipped).toBeLessThan(full);
  await expect(toggle).toHaveAttribute("aria-expanded", "false");

  await toggle.click();
  const hide = example.getByRole("button", { name: "Hide the full card" });
  await expect(hide).toHaveAttribute("aria-expanded", "true");
  await expect.poll(() => card.evaluate((img) => img.parentElement!.getBoundingClientRect().height)).toBeGreaterThanOrEqual(full - 1);

  await hide.click();
  await expect(example.getByRole("button", { name: "Show the full card" })).toBeVisible();
});

test(`${OUTCOME} the worked example ends with the booking and the reply`, async ({ page }) => {
  await page.goto("/");

  const example = page.getByRole("figure", { name: "One request from start to finish" });
  const [, opening, ...rest] = worked.reply.body.split("\n\n");
  await expect(example).toContainText("A medium one is free all three nights");
  await expect(example).toContainText("PawDesk booked that kennel and sent this reply:");
  await expect(example.getByText("Sent", { exact: true })).toBeVisible();
  await expect(example.getByText(worked.reply.subject, { exact: true })).toBeVisible();
  await expect(example.getByText(opening, { exact: true })).toBeVisible();
  const signOff = example.getByText(rest.at(-1)!.split("\n").at(-1)!);
  await expect(signOff).toBeHidden();

  await example.getByRole("button", { name: "Show the full reply" }).click();
  await expect(signOff).toBeVisible();
  await expect(example.getByRole("button", { name: "Hide the rest" })).toHaveAttribute("aria-expanded", "true");
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

test(`${NAV_TRY} the navigation's Try a request link scrolls to the Try panel`, async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation").getByRole("link", { name: "Try a request", exact: true }).click();
  await expect(page).toHaveURL(/\/#try$/);
  await expect(page.getByRole("heading", { name: "Try a request", level: 2 })).toBeInViewport();
});

test(`${NAV_TRY} the navigation's Try a request link opens the Try panel from another page`, async ({ page }) => {
  await page.goto("/requests");
  await page.getByRole("navigation").getByRole("link", { name: "Try a request", exact: true }).click();
  await expect(page).toHaveURL(/\/#try$/);
  await expect(page.getByRole("heading", { name: "Try a request", level: 2 })).toBeInViewport();
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

  const strip = page.getByRole("figure", { name: "Two vaccines against a hypothetical dog's stay from March 24 to 27" });
  await expect(strip).toContainText("Covers the stay");
  await expect(strip).toContainText("Expires during the stay");
  await expect(page.locator("#rules")).toContainText("20 to under 50 lb");
});

test(`${EXAMPLE} the coverage diagram describes a hypothetical dog, not a pet on file`, async ({ page }) => {
  await page.goto("/");
  const strip = page.getByRole("figure", { name: "Two vaccines against a hypothetical dog's stay from March 24 to 27" });
  await expect(strip).toContainText("A hypothetical dog");
  await expect(strip).not.toContainText("Biscuit");
  await expect(strip).toContainText("Covers the stay");
  await expect(strip).toContainText("Expires during the stay");
});
