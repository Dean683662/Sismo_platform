import { expect, test } from "@playwright/test";

import { openModule, signIn } from "./helpers";

test("import the IGP historical catalog and show its audited skipped-row count", async ({ page }) => {
	await signIn(page);

	const sourceId = "00000000-0000-4000-8000-000000000001";
	let imported = false;
	const run = {
		id: "00000000-0000-4000-8000-000000000002",
		source_id: sourceId,
		started_at: "2026-10-18T12:00:00Z",
		finished_at: "2026-10-18T12:00:05Z",
		status: "succeeded",
		records_seen: 1099,
		records_inserted: 1040,
		records_updated: 0,
		records_duplicated: 0,
		records_skipped: 59,
		error_summary: null,
	};
	await page.route("**/api/v1/sources", async (route) => {
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify([{
				id: sourceId,
				provider_key: "igp",
				name: "Catálogo sísmico del IGP",
				organization: "Instituto Geofísico del Perú",
				base_url: "https://ultimosismo.igp.gob.pe/repositorio/datos-sismicos",
				source_type: "official_api",
				is_verified: true,
				status: "active",
				last_sync_at: imported ? run.finished_at : null,
				last_success_at: imported ? run.finished_at : null,
				last_run: imported ? run : null,
			}]),
		});
	});
	await page.route(`**/api/v1/sources/${sourceId}/backfill`, async (route) => {
		expect(route.request().method()).toBe("POST");
		expect(route.request().headers()["x-csrf-token"]).toBeTruthy();
		imported = true;
		await route.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify(run),
		});
	});

	await openModule(page, "Fuentes de datos", "Fuentes de datos");
	await page.getByRole("button", { name: "Importar catálogo histórico" }).click();
	await expect(page.getByRole("status")).toContainText("1040 nuevos");
	await expect(page.getByRole("status")).toContainText("59 omitidos por datos incompletos");
	await expect(page.locator(".source-metrics").getByText("59", { exact: true })).toBeVisible();
});
