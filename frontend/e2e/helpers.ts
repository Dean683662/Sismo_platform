import { expect, type Page } from "@playwright/test";

export const e2eEmail = "e2e-admin@example.com";
export const e2ePassword = "E2E-Only-Password-2026";

export async function signIn(page: Page) {
	await page.goto("/");
	await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
	await page.getByLabel("Correo electrónico").fill(e2eEmail);
	await page.getByLabel("Contraseña").fill(e2ePassword);
	const loginResponse = page.waitForResponse((response) =>
		response.url().endsWith("/api/v1/auth/login") && response.request().method() === "POST",
	);
	await page.getByRole("button", { name: "Continuar" }).click();
	const response = await loginResponse;
	expect(response.status(), `Sign-in API response: ${await response.text()}`).toBe(200);
	await expect(page.getByRole("navigation", { name: "Navegación principal" })).toBeVisible();
}

export async function openModule(page: Page, name: string, heading: string) {
	await page.getByRole("link", { name, exact: true }).click();
	await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible();
}
