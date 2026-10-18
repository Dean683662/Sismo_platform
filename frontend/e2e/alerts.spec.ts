import { expect, test } from "@playwright/test";

import { openModule, signIn } from "./helpers";

test("create an alert rule, test against a stored event, and read delivery history", async ({ page }) => {
	expect((await page.request.get("/api/v1/alerts/rules")).status()).toBe(401);
	await signIn(page);
	await openModule(page, "Centro de alertas", "Centro de alertas");

	const ruleName = `E2E alerta ${Date.now()}`;
	await page.getByLabel("Nombre de la regla").fill(ruleName);
	await page.getByLabel("Magnitud mínima").fill("0");
	await page.getByLabel("Canal de entrega").selectOption("in_app");
	await page.getByRole("button", { name: "Guardar regla" }).click();
	await expect(page.getByText(ruleName, { exact: true })).toBeVisible();

	const rule = page.locator(".alert-rule").filter({ hasText: ruleName });
	await rule.getByRole("button", { name: "Probar" }).click();
	await expect(page.getByText("Entregada", { exact: true })).toBeVisible();
	await expect(page.getByText(/intentos 1/).first()).toBeVisible();

	await page.reload();
	await expect(page.getByText(ruleName, { exact: true })).toBeVisible();
	await expect(page.getByText("Entregada", { exact: true })).toBeVisible();
});
