# Demo de Professional en tu PC (Windows), en un comando:
#   clic derecho → "Ejecutar con PowerShell"   (o: powershell -ExecutionPolicy Bypass -File demo.ps1)
# Levanta todo con Docker Desktop, siembra los 3 clientes de demo y da los enlaces.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host "X Falta Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
  Read-Host "Pulsa Enter para salir"; exit 1
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  (Get-Content ".env") `
    -replace '^ADMIN_1_USER=.*', 'ADMIN_1_USER=professional' `
    -replace '^ADMIN_1_PASS=.*', 'ADMIN_1_PASS=Professional-Demo-2026' `
    -replace '^EMAILS_ENABLED=.*', 'EMAILS_ENABLED=false' | Set-Content ".env"
  Write-Host "OK .env creado (panel: professional / Professional-Demo-2026)" -ForegroundColor Green
  Write-Host "   Para IA en vivo (leer anamnesis / generar plan): añade ANTHROPIC_API_KEY al .env"
}

Write-Host "-> Levantando la demo (la primera vez tarda unos minutos)..." -ForegroundColor Cyan
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

Write-Host "-> Esperando a la API..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
  try {
    Invoke-WebRequest -Uri "http://localhost:8000/api/docs" -UseBasicParsing -TimeoutSec 2 | Out-Null
    $ok = $true; break
  } catch { Start-Sleep -Seconds 2 }
}
if (-not $ok) { Write-Host "X La API no arranca; mira: docker compose logs api" -ForegroundColor Red; Read-Host "Enter para salir"; exit 1 }

Write-Host "-> Sembrando los 3 clientes de demo..." -ForegroundColor Cyan
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T api python scripts/demo_seed.py

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Yellow
Write-Host "  DEMO LISTA" -ForegroundColor Yellow
Write-Host "  Panel del coach:    http://localhost:5173"
Write-Host "  Página de planes:   http://localhost:5173/planes"
Write-Host "  Login del panel:    (usuario y contraseña del .env)"
Write-Host "  Enlaces del portal: arriba, impresos por el script"
Write-Host "  Guión de la demo:   DEMO.md"
Write-Host "  Reiniciar la demo:  re-ejecuta este script"
Write-Host "  Apagar:             docker compose -f docker-compose.yml -f docker-compose.dev.yml down"
Write-Host "=====================================================" -ForegroundColor Yellow
Read-Host "Pulsa Enter para cerrar"
