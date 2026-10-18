import { expect, test } from "@playwright/test";

import { e2eEmail, e2ePassword, signIn } from "./helpers";

test("auth failure then sign-in, protected navigation, reload, and logout", async ({ page }) => {
	const anonymousResponse = await page.request.get("/api/v1/alerts/rules");
	expect(anonymousResponse.status()).toBe(401);

	await page.goto("/");
	await page.getByLabel("Correo electrónico").fill(e2eEmail);
	await page.getByLabel("Contraseña").fill("incorrect-password");
	await page.getByRole("button", { name: "Continuar" }).click();
	await expect(page.getByRole("alert")).toContainText("No se pudo iniciar sesión");

	await signIn(page);
	await page.getByRole("link", { name: "Centro de alertas", exact: true }).click();
	await expect(page.getByRole("heading", { name: "Centro de alertas", level: 1 })).toBeVisible();
	await page.reload();
	await expect(page.getByRole("heading", { name: "Centro de alertas", level: 1 })).toBeVisible();

	await page.getByRole("button", { name: "Cerrar sesión" }).click();
	await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
	expect((await page.request.get("/api/v1/alerts/rules")).status()).toBe(401);
});
