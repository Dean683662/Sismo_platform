import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const frontendDirectory = resolve(scriptDirectory, "..");
const workDirectory = mkdtempSync(join(tmpdir(), "sismo-platform-e2e-"));
const repositoryRoot = resolve(frontendDirectory, "..");
const environment = {
	...process.env,
	APP_ENV: "development",
	DATABASE_URL: `sqlite+pysqlite:///./${basename(workDirectory)}/sismo-e2e.sqlite`,
	SUPABASE_DATABASE_URL: "",
	DB_HOST: "",
	DB_PORT: "",
	DB_DATABASE: "",
	DB_USERNAME: "",
	DB_PASSWORD: "",
	JWT_SECRET_KEY: "e2e-only-secret-key-that-is-long-enough-for-testing-123456",
	BOOTSTRAP_ADMIN_EMAIL: "e2e-admin@example.com",
	BOOTSTRAP_ADMIN_PASSWORD: "E2E-Only-Password-2026",
	PYTHONPATH: repositoryRoot,
	SISMO_E2E_WORKDIR: workDirectory,
};

let exitCode = 1;
try {
	const result = spawnSync(
		process.execPath,
		[join(frontendDirectory, "node_modules", "@playwright", "test", "cli.js"), "test", ...process.argv.slice(2)],
		{ cwd: frontendDirectory, env: environment, stdio: "inherit" },
	);
	if (result.error) {
		throw result.error;
	}
	exitCode = result.status ?? 1;
} catch (error) {
	console.error("Could not run the isolated browser test suite:", error);
} finally {
	try {
		rmSync(workDirectory, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
	} catch (error) {
		console.error(`Could not clean up isolated browser test directory ${workDirectory}:`, error);
		exitCode = 1;
	}
}

process.exitCode = exitCode;
