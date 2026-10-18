param(
	[string]$ComposeFile = "infra/docker-compose.yml"
)

$ErrorActionPreference = "Stop"
$container = (docker compose -f $ComposeFile ps -q db).Trim()
if (-not $container) {
	throw "The local Compose PostgreSQL container is not running. This script does not connect to Supabase."
}

$restoreDatabase = "sismo_restore_check_$([guid]::NewGuid().ToString('N').Substring(0, 12))"
$backupPath = "/tmp/$restoreDatabase.dump"
$created = $false

try {
	docker compose -f $ComposeFile exec -T db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB" -f "$1"' sh $backupPath
	if ($LASTEXITCODE -ne 0) { throw "pg_dump failed." }

	docker compose -f $ComposeFile exec -T db sh -c 'createdb -U "$POSTGRES_USER" "$1"' sh $restoreDatabase
	if ($LASTEXITCODE -ne 0) { throw "Could not create the isolated restore database." }
	$created = $true

	docker compose -f $ComposeFile exec -T db sh -c 'pg_restore --exit-on-error --no-owner -U "$POSTGRES_USER" -d "$1" "$2"' sh $restoreDatabase $backupPath
	if ($LASTEXITCODE -ne 0) { throw "pg_restore failed." }

	$revision = (docker compose -f $ComposeFile exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$1" -Atqc "SELECT version_num FROM alembic_version"' sh $restoreDatabase).Trim()
	if ($LASTEXITCODE -ne 0 -or -not $revision) { throw "The restored database has no Alembic revision." }
	$tableCount = [int](docker compose -f $ComposeFile exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$1" -Atqc "SELECT count(*) FROM information_schema.tables WHERE table_schema = ''public'' AND table_type = ''BASE TABLE''"' sh $restoreDatabase).Trim()
	if ($LASTEXITCODE -ne 0 -or $tableCount -lt 10) { throw "The restored schema is incomplete ($tableCount public tables)." }

	Write-Output "Backup restore verified in isolated database: revision=$revision, public_tables=$tableCount."
}
finally {
	if ($created) {
		docker compose -f $ComposeFile exec -T db sh -c 'dropdb --if-exists -U "$POSTGRES_USER" "$1"' sh $restoreDatabase
		if ($LASTEXITCODE -ne 0) { [Console]::Error.WriteLine("Could not remove isolated validation database $restoreDatabase.") }
	}
	docker compose -f $ComposeFile exec -T db rm -f $backupPath
	if ($LASTEXITCODE -ne 0) { [Console]::Error.WriteLine("Could not remove temporary backup $backupPath from the local container.") }
}
