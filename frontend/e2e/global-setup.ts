import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export default function globalSetup() {
	const frontendDirectory = dirname(fileURLToPath(import.meta.url));
	const repositoryRoot = resolve(frontendDirectory, "../..");
	const python = existsSync(join(repositoryRoot, ".venv", "Scripts", "python.exe"))
		? join(repositoryRoot, ".venv", "Scripts", "python.exe")
		: "python";
	const workDirectory = process.env.SISMO_E2E_WORKDIR;
	if (!workDirectory) {
		throw new Error("SISMO_E2E_WORKDIR is required for isolated browser tests.");
	}
	const result = spawnSync(python, [join(repositoryRoot, "tests", "e2e", "seed_database.py")], {
		cwd: dirname(workDirectory),
		env: process.env,
		encoding: "utf8",
	});
	if (result.status !== 0) {
		throw new Error(`Could not prepare isolated E2E database:\n${result.stdout}\n${result.stderr}`);
	}
}
