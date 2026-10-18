import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { openModule, signIn } from "./helpers";

test("create and export a persisted event report; pages pass automated WCAG checks", async ({ page }) => {
	expect((await page.request.get("/api/v1/reports")).status()).toBe(401);
	await signIn(page);

	const dashboardAccessibility = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
	expect(dashboardAccessibility.violations).toEqual([]);

	await openModule(page, "Reportes", "Reportes");
	const accessibility = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
	expect(accessibility.violations).toEqual([]);

	await page.getByLabel("Tipo de reporte").selectOption("events");
	await page.getByLabel("Clave de fuente").fill("e2e");
	await page.getByRole("button", { name: "Generar reporte" }).click();
	const reportRow = page.getByRole("row").filter({ hasText: "source_key: e2e" });
	await expect(reportRow).toBeVisible();
	await expect(reportRow).toContainText("1");

	const downloadPromise = page.waitForEvent("download");
	await reportRow.getByRole("button", { name: "CSV" }).click();
	const download = await downloadPromise;
	expect(download.suggestedFilename()).toMatch(/^reporte-events-.+\.csv$/);

	await page.reload();
	await expect(page.getByRole("row").filter({ hasText: "source_key: e2e" })).toBeVisible();
});
