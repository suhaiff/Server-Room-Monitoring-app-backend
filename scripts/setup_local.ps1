$ErrorActionPreference = "Stop"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host "VTAB Sentinel local configuration is ready."
Write-Host "Run: docker compose up --build"
Write-Host "Dashboard: http://localhost:5173"
Write-Host "Independent Test Lab: http://localhost:5174"
