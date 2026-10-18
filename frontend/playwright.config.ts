import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(frontendDirectory, "..");
const workDirectory = process.env.SISMO_E2E_WORKDIR;
if (!workDirectory) {
	throw new Error("Run browser tests through `npm run test:e2e` to create an isolated test database.");
}
const python = existsSync(join(repositoryRoot, ".venv", "Scripts", "python.exe"))
	? join(repositoryRoot, ".venv", "Scripts", "python.exe")
	: "python";
const adminEmail = "e2e-admin@example.com";
const adminPassword = "E2E-Only-Password-2026";
const databaseUrl = `sqlite+pysqlite:///./${workDirectory.split(/[\\/]/).pop()}/sismo-e2e.sqlite`;
const sharedEnvironment = {
	...process.env,
	APP_ENV: "development",
	DATABASE_URL: databaseUrl,
	SUPABASE_DATABASE_URL: "",
	DB_HOST: "",
	DB_PORT: "",
	DB_DATABASE: "",
	DB_USERNAME: "",
	DB_PASSWORD: "",
	JWT_SECRET_KEY: "e2e-only-secret-key-that-is-long-enough-for-testing-123456",
	BOOTSTRAP_ADMIN_EMAIL: adminEmail,
	BOOTSTRAP_ADMIN_PASSWORD: adminPassword,
	PYTHONPATH: repositoryRoot,
};

export default defineConfig({
	testDir: "./e2e",
	fullyParallel: false,
	forbidOnly: Boolean(process.env.CI),
	retries: process.env.CI ? 1 : 0,
	reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
	outputDir: "test-results",
	globalSetup: "./e2e/global-setup.ts",
	workers: 1,
	use: {
		baseURL: "http://127.0.0.1:5174",
		trace: "retain-on-failure",
		screenshot: "only-on-failure",
		video: "retain-on-failure",
		...devices["Desktop Chrome"],
	},
	webServer: [
		{
			command: `"${python}" -m uvicorn backend.main:app --host 127.0.0.1 --port 8010`,
			cwd: tmpdir(),
			env: sharedEnvironment,
			url: "http://127.0.0.1:8010/ready",
			reuseExistingServer: false,
			timeout: 120_000,
		},
		{
			command: "npm run dev -- --host 127.0.0.1 --port 5174 --strictPort",
			cwd: frontendDirectory,
			url: "http://127.0.0.1:5174",
			env: { ...sharedEnvironment, VITE_API_PROXY_TARGET: "http://127.0.0.1:8010" },
			reuseExistingServer: false,
			timeout: 120_000,
		},
	],
});
