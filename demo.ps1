# Demo de Professional en tu PC (Windows), en un comando:
#   clic derecho → "Ejecutar con PowerShell"   (o: powershell -ExecutionPolicy Bypass -File demo.ps1)
# Levanta todo con Docker Desktop, siembra los 4 clientes de demo y da los enlaces.
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

# ACTUALIZARSE PRIMERO: el doble clic debe traer la ultima version del codigo.
# Sin esto, el lanzador levantaba lo que hubiera en la carpeta aunque los
# cambios llevaran semanas subidos (paso: la web "no cambiaba nunca").
#
# Y si NO puede actualizar, PARA. Antes avisaba en amarillo y seguia, y eso
# costo una tarde entera: `git pull --ff-only` se negaba (el .gitattributes
# renormaliza los finales de linea y deja el arbol "sucio"), el script
# reconstruia el Dockerfile ANTIGUO y el contenedor se quedaba en bucle con
# "exec /code/entrypoint.sh: no such file or directory" — un error que no tiene
# NADA que ver con la causa real, que era simplemente codigo viejo.
#
# Es `reset --hard` y no `pull` a proposito: esta carpeta es una INSTALACION,
# no un sitio donde programar. Lo unico que importa aqui (.env, storage/) no
# esta versionado, asi que el reset no lo toca.
if ((Get-Command git -ErrorAction SilentlyContinue) -and (Test-Path ".git")) {
  Write-Host "-> Trayendo la ultima version del codigo..." -ForegroundColor Cyan
  $rama = (cmd /c "git rev-parse --abbrev-ref HEAD 2>nul").Trim()
  if (-not $rama -or $rama -eq "HEAD") {
    Write-Host "X Esta carpeta no esta en ninguna rama de git." -ForegroundColor Red
    Write-Host "  Arreglalo con:  git checkout claude/dqr-white-label-4ojp01"
    Read-Host "Pulsa Enter para salir"; exit 1
  }
  cmd /c "git fetch origin $rama 2>&1"
  if ($LASTEXITCODE -ne 0) {
    Write-Host "X No se pudo descargar el codigo (¿sin conexion?)." -ForegroundColor Red
    Write-Host "  Comprueba internet y vuelve a lanzarlo."
    Read-Host "Pulsa Enter para salir"; exit 1
  }
  cmd /c "git reset --hard origin/$rama 2>&1"
  if ($LASTEXITCODE -ne 0) {
    Write-Host "X No se pudo poner la carpeta al dia." -ForegroundColor Red
    Write-Host "  Paro aqui a proposito: seguir significaria levantar codigo viejo."
    Read-Host "Pulsa Enter para salir"; exit 1
  }
  $commit = (cmd /c "git log -1 --format=%h %s").Trim()
  Write-Host "OK Codigo al dia: $rama ($commit)" -ForegroundColor Green
}

# En dev el servicio `web` es Vite (5173), no Caddy: sus 80 y 443 quedarian
# publicados para nada y en Windows el 80 suele estar cogido (IIS, Skype, otro
# proyecto). Si no puede reservarlos, el contenedor no arranca — pero la API si,
# asi que el lanzador daba la demo por lista y localhost:5173 no abria.
# Apartados a puertos altos; en produccion siguen siendo 80 y 443.
$env:HTTP_PORT = "8380"
$env:HTTPS_PORT = "8343"

# Apaga ESTE proyecto si estaba (a medias o entero): re-ejecutar = reiniciar.
# Sin esto, el chequeo de puertos de abajo se tropezaba con NUESTROS propios
# contenedores y el script abortaba culpando a otro proyecto.
# Va por cmd a propósito: con $ErrorActionPreference=Stop, un `2>$null` de
# PowerShell 5.1 convierte el stderr normal de compose en error fatal.
cmd /c "docker compose -f docker-compose.yml -f docker-compose.dev.yml down --remove-orphans >nul 2>&1"

# Si DQR (u otro proyecto) esta arrancado en este PC, usa los mismos puertos:
# hay que pararlo primero (los proyectos estan AISLADOS, pero no caben a la vez).
foreach ($port in 5173, 8000, 5432, 8025, 8380, 8343) {
  $busy = Test-NetConnection -ComputerName localhost -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
  if ($busy) {
    Write-Host "X El puerto $port ya esta en uso. ¿Tienes DQR u otro proyecto arrancado?" -ForegroundColor Red
    Write-Host "  Paralo primero desde su carpeta:  docker compose down"
    Read-Host "Pulsa Enter para salir"; exit 1
  }
}

Write-Host "-> Levantando la demo (la primera vez tarda unos minutos)..." -ForegroundColor Cyan
# El codigo de salida IMPORTA: si un contenedor no puede reservar su puerto,
# compose falla pero los que si arrancaron siguen en pie. Sin esta comprobacion,
# la API respondia, el script decia "DEMO LISTA" y la web no abria.
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "X Docker no ha podido levantar la demo (el motivo va justo arriba)." -ForegroundColor Red
  Read-Host "Pulsa Enter para salir"; exit 1
}

Write-Host "-> Esperando a la API..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
  try {
    Invoke-WebRequest -Uri "http://localhost:8000/api/docs" -UseBasicParsing -TimeoutSec 2 | Out-Null
    $ok = $true; break
  } catch { Start-Sleep -Seconds 2 }
}
if (-not $ok) {
  $logs = (cmd /c "docker compose -f docker-compose.yml -f docker-compose.dev.yml logs api --tail 40 --no-color 2>&1") -join "`n"
  Write-Host ""
  Write-Host "X La API no arranca. Este es el motivo, tal cual:" -ForegroundColor Red
  Write-Host "-----------------------------------------------------" -ForegroundColor DarkGray
  Write-Host $logs
  Write-Host "-----------------------------------------------------" -ForegroundColor DarkGray
  # Traducir el error que mas despista: esa ruta se dejo de usar, asi que si
  # aparece es que la imagen se construyo con un Dockerfile antiguo.
  if ($logs -match "/code/entrypoint\.sh") {
    Write-Host "-> Ese mensaje significa IMAGEN VIEJA: /code/entrypoint.sh ya no se usa." -ForegroundColor Yellow
    Write-Host "   Reconstruyela desde cero:"
    Write-Host "   docker compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache api"
  } else {
    Write-Host "Copia estas lineas (o hazles captura) para diagnosticar." -ForegroundColor Yellow
  }
  Read-Host "Enter para salir"; exit 1
}

Write-Host "-> Sembrando los 4 clientes de demo..." -ForegroundColor Cyan
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T api python scripts/demo_seed.py

# ESPERAR TAMBIEN A LA WEB. El lanzador solo miraba la API, asi que cualquier
# problema del contenedor `web` acababa en un "DEMO LISTA" con localhost:5173
# sin abrir — el peor final posible: parece que todo fue bien. Va despues del
# seed a proposito: en dev el contenedor hace `npm install` y la primera vez
# tarda varios minutos; darle ese margen extra evita falsos negativos.
Write-Host "-> Esperando al panel (la primera vez instala dependencias, tarda)..." -ForegroundColor Cyan
$webOk = $false
for ($i = 0; $i -lt 150; $i++) {
  try {
    Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 2 | Out-Null
    $webOk = $true; break
  } catch { Start-Sleep -Seconds 2 }
}
if (-not $webOk) {
  Write-Host ""
  Write-Host "X El panel no responde en http://localhost:5173. Este es el motivo:" -ForegroundColor Red
  Write-Host "-----------------------------------------------------" -ForegroundColor DarkGray
  cmd /c "docker compose -f docker-compose.yml -f docker-compose.dev.yml logs web --tail 40 --no-color 2>&1"
  Write-Host "-----------------------------------------------------" -ForegroundColor DarkGray
  Write-Host "Copia estas lineas (o hazles captura) para diagnosticar." -ForegroundColor Yellow
  Read-Host "Enter para salir"; exit 1
}

# Decir las credenciales EXACTAS, comprobadas contra la base de datos. Antes
# esta linea decia "usuario y contraseña del .env" y quien no abria el fichero
# se quedaba adivinando delante de un "credenciales incorrectas".
$login = (cmd /c "docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T api python scripts/check_login.py 2>&1") -join " "
if (-not $login) { $login = "(no se pudo comprobar: mira ADMIN_1_USER y ADMIN_1_PASS en el .env)" }

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Yellow
Write-Host "  DEMO LISTA" -ForegroundColor Yellow
Write-Host "  Panel del coach:    http://localhost:5173"
Write-Host "  Página de planes:   http://localhost:5173/planes"
Write-Host "  Login del panel:    $login"
Write-Host "  Enlaces del portal: arriba, impresos por el script"
Write-Host "  Guión de la demo:   DEMO.md"
Write-Host "  Reiniciar la demo:  re-ejecuta este script"
Write-Host "  Apagar:             docker compose -f docker-compose.yml -f docker-compose.dev.yml down"
Write-Host "=====================================================" -ForegroundColor Yellow
Read-Host "Pulsa Enter para cerrar"
