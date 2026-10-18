param(
	[string]$BaseUrl = "http://localhost:8080",
	[switch]$Continuous,
	[int]$IntervalSeconds = 30
)

$ErrorActionPreference = "Stop"
if ($IntervalSeconds -lt 5 -or $IntervalSeconds -gt 3600) {
	throw "IntervalSeconds must be between 5 and 3600."
}

do {
	$failed = $false
	foreach ($endpoint in @("/health", "/ready")) {
		try {
			$response = Invoke-WebRequest -Uri "$($BaseUrl.TrimEnd('/'))$endpoint" -TimeoutSec 5
			if ($response.StatusCode -ne 200) {
				throw "Unexpected HTTP status $($response.StatusCode)."
			}
			$body = $response.Content | ConvertFrom-Json
			$expectedStatus = if ($endpoint -eq "/health") { "ok" } else { "ready" }
			if ($body.status -ne $expectedStatus) {
				throw "Unexpected endpoint status '$($body.status)'."
			}
			Write-Output "$(Get-Date -Format o) $endpoint healthy"
		}
		catch {
			$failed = $true
			[Console]::Error.WriteLine("$(Get-Date -Format o) $endpoint unhealthy: $($_.Exception.Message)")
		}
	}
	if ($failed -and -not $Continuous) {
		exit 1
	}
	if ($Continuous) {
		Start-Sleep -Seconds $IntervalSeconds
	}
} while ($Continuous)
