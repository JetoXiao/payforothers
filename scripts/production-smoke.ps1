param(
    [string]$BaseUrl = "http://127.0.0.1:8080"
)

$ErrorActionPreference = "Stop"
$resolvedBaseUrl = $BaseUrl.TrimEnd("/")

Write-Host "Checking health endpoint..."
$health = Invoke-RestMethod -Method Get -Uri "$resolvedBaseUrl/health"
if ($null -eq $health) {
    throw "Health endpoint returned an empty response."
}

Write-Host "Checking public configuration endpoint..."
$publicConfig = Invoke-RestMethod -Method Get -Uri "$resolvedBaseUrl/api/v1/public/config"
if ($null -eq $publicConfig) {
    throw "Public configuration endpoint returned an empty response."
}

Write-Host "Smoke checks passed for $resolvedBaseUrl"
