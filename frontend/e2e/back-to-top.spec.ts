import { expect, test, type Page } from "@playwright/test";

import { specTag } from "../tests/spec-tag";

const TOP = specTag("run-dashboard", "Long pages offer a way back to the top");

const button = (page: Page) => page.getByRole("button", { name: "Back to top" });

// Playwright's role lookup still finds inert elements, so "hidden" is checked as the
// browser applies it: transparent, inert, and refusing focus.
async function expectHidden(page: Page) {
  await expect(button(page)).toHaveCSS("opacity", "0");
  await expect(button(page)).toHaveJSProperty("inert", true);
  expect(await button(page).evaluate((b: HTMLButtonElement) => (b.focus(), document.activeElement === b))).toBe(false);
}

async function scrollPastFirstScreen(page: Page) {
  await page.evaluate(() => window.scrollTo(0, window.innerHeight * 2));
  await expect(button(page)).toHaveJSProperty("inert", false);
  await expect(button(page)).toHaveCSS("opacity", "1");
}

test(`${TOP} the button is hidden and unfocusable at the top`, async ({ page }) => {
  await page.goto("/");
  await expectHidden(page);
});

test(`${TOP} scrolling past the first screen shows it, pressing it returns to the top`, async ({ page }) => {
  await page.goto("/");
  await scrollPastFirstScreen(page);
  const box = (await button(page).boundingBox())!;
  const viewport = page.viewportSize()!;
  expect(box.x).toBeGreaterThan(viewport.width / 2);
  expect(box.y).toBeGreaterThan(viewport.height / 2);

  await button(page).click();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
  await expectHidden(page);
});

test(`${TOP} with reduced motion the page jumps to the top at once`, async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await scrollPastFirstScreen(page);

  // Record the scroll position on the next frame after the press: a smooth scroll would
  // still be partway down, a jump is already at 0.
  await button(page).evaluate((b) => {
    const w = window as typeof window & { afterPress?: number };
    b.addEventListener("click", () => requestAnimationFrame(() => (w.afterPress = window.scrollY)));
  });
  await button(page).click();
  await expect.poll(() => page.evaluate(() => (window as typeof window & { afterPress?: number }).afterPress)).toBe(0);
});
