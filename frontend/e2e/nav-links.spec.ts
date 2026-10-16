import { expect, test } from "@playwright/test";

import { specTag } from "../tests/spec-tag";

const LINKS = specTag("run-dashboard", "The navigation links to the source code and the portfolio");

for (const { name, href } of [
  { name: "Source code", href: "https://github.com/Pohi11/PawDesk" },
  { name: "Portfolio", href: "https://pohi.me/" },
]) {
  test(`${LINKS} the ${name} link opens ${href} in a new tab`, async ({ page }) => {
    await page.goto("/");
    const link = page.getByRole("navigation").getByRole("link", { name: `${name} (opens in a new tab)` });
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("href", href);
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(link).toHaveAttribute("rel", /noopener/);
  });
}
