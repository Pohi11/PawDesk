import { expect, test } from "@playwright/test";

import { specTag } from "../tests/spec-tag";

const TOUCH = specTag("run-dashboard", "Tapping on a touch screen draws no highlight");

test.describe("on a phone", () => {
  test.use({ viewport: { width: 393, height: 851 }, isMobile: true, hasTouch: true });

  test(`${TOUCH} tapping a button draws no tap highlight`, async ({ page }) => {
    await page.goto("/");
    const button = page.getByRole("button", { name: /Make one up/ });
    await button.tap();
    const highlight = await button.evaluate((el) => getComputedStyle(el).getPropertyValue("-webkit-tap-highlight-color"));
    expect(highlight).toBe("rgba(0, 0, 0, 0)");
  });

  test(`${TOUCH} tapping the request text box focuses it without an outline`, async ({ page }) => {
    await page.goto("/");
    const box = page.getByRole("textbox").first();
    await box.tap();
    await expect(box).toBeFocused();
    expect(await box.evaluate((el) => getComputedStyle(el).outlineStyle)).toBe("none");
  });
});

test(`${TOUCH} moving with the keyboard shows the focus outline`, async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  const outline = await page.evaluate(() => {
    const el = document.activeElement;
    return el && el !== document.body ? getComputedStyle(el).outlineStyle : "nothing focused";
  });
  expect(outline).toBe("solid");
});
