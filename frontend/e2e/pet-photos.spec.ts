import { expect, type Page, test } from "@playwright/test";

import { specTag } from "../tests/spec-tag";

const SHOWN = specTag("pet-photos", "Photos appear on the requests list and the run page");
const PLACEHOLDER = specTag("pet-photos", "A request without a matched pet shows a placeholder");

async function sendSample(page: Page, title: string): Promise<string> {
  await page.goto("/demo");
  await page.getByText(title, { exact: true }).click();
  await page.getByRole("button", { name: "Send and watch it run" }).click();
  await page.waitForURL(/\/requests\/[0-9a-f-]{36}$/);
  return new URL(page.url()).pathname;
}

test(`${SHOWN} Biscuit's Beagle photo shows on the live run and the list`, async ({ page }) => {
  const path = await sendSample(page, "Clean boarding request");

  // No reload: the photo arrives with the live updates once intake matches Biscuit.
  const photo = page.getByRole("img", { name: "Photo for Biscuit" });
  await expect(photo).toBeVisible();
  await expect(photo).toHaveAttribute("src", "/pets/beagle.jpg");
  await expect(page.getByText("The checks passed it, so it went out without a person.")).toBeVisible();

  await page.goto("/");
  const row = page.locator(`a[href="${path}"]`);
  await expect(row.getByRole("img", { name: "Photo for Biscuit" })).toHaveAttribute("src", "/pets/beagle.jpg");
});

test(`${PLACEHOLDER} a pet not on file gets the paw placeholder`, async ({ page }) => {
  const path = await sendSample(page, "Pet not on file");

  // Wait for the run to rest, so this is the final state and not the moment before intake.
  // (Its outcome doesn't matter here: no recorded responses exist for this sample, so it
  // stops at extraction, and either way no pet is matched.)
  await expect(page.getByText("Working on it.")).toHaveCount(0);
  await expect(page.getByRole("img", { name: "No pet matched yet" })).toBeVisible();
  await expect(page.getByRole("img", { name: /^Photo for/ })).toHaveCount(0);

  await page.goto("/");
  const row = page.locator(`a[href="${path}"]`);
  await expect(row.getByRole("img", { name: "No pet matched yet" })).toBeVisible();
  await expect(row.getByRole("img", { name: /^Photo for/ })).toHaveCount(0);
});
