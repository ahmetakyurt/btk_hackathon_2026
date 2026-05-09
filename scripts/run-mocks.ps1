# Launch all 3 mock platform services in separate PowerShell windows.
# Usage (from project root):
#   .\scripts\run-mocks.ps1
#
# Each window auto-reloads on file changes. Close the window to stop.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$services = @(
    @{ Name = "trendyol"; Port = 9001 }
    @{ Name = "amazon";   Port = 9002 }
    @{ Name = "own_site"; Port = 9003 }
)

foreach ($svc in $services) {
    $dir = Join-Path $root "mock_services\$($svc.Name)"
    Write-Host "Starting mock-$($svc.Name) on :$($svc.Port) ..."
    Start-Process pwsh -ArgumentList @(
        "-NoExit",
        "-Command",
        "Set-Location '$dir'; uv run uvicorn main:app --port $($svc.Port) --reload"
    ) -WindowStyle Normal
}

Write-Host "`nAll mock services launched. Health checks:"
Write-Host "  curl http://localhost:9001/health   # trendyol"
Write-Host "  curl http://localhost:9002/health   # amazon"
Write-Host "  curl http://localhost:9003/health   # own_site"
