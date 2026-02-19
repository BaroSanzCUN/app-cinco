# Script Maestro de Pruebas - Deployment Manual
# Ejecuta todas las verificaciones necesarias antes de deployment

Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host "     PRUEBA MANUAL DE DEPLOYMENT - APP CINCO                  " -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Cyan

Write-Host ""
$startTime = Get-Date

# Funcion para verificar comandos
function Test-Command {
    param($Command)
    try {
        $null = & $Command --version 2>&1
        return $true
    } catch {
        return $false
    }
}

# ========== FASE 1: VERIFICACIÓN DE ENTORNO ==========
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "FASE 1: VERIFICACIÓN DE ENTORNO" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

# Python
Write-Host "[Python]" -NoNewline
if (Test-Command "python") {
    $pythonVersion = python --version
    Write-Host " OK - $pythonVersion" -ForegroundColor Green
} else {
    Write-Host " FAIL - No encontrado" -ForegroundColor Red
}

# Node.js
Write-Host "[Node.js]" -NoNewline
if (Test-Command "node") {
    $nodeVersion = node --version
    Write-Host " OK - $nodeVersion" -ForegroundColor Green
} else {
    Write-Host " FAIL - No encontrado" -ForegroundColor Red
}

# npm
Write-Host "[npm]" -NoNewline
if (Test-Command "npm") {
    $npmVersion = npm --version
    Write-Host " OK - v$npmVersion" -ForegroundColor Green
} else {
    Write-Host " FAIL - No encontrado" -ForegroundColor Red
}

# Git
Write-Host "[Git]" -NoNewline
if (Test-Command "git") {
    $gitVersion = git --version
    Write-Host " OK - $gitVersion" -ForegroundColor Green
} else {
    Write-Host " FAIL - No encontrado" -ForegroundColor Red
}

Write-Host ""
Start-Sleep -Seconds 2

# ========== FASE 2: VERIFICACIÓN DE ESTRUCTURA ==========
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "FASE 2: VERIFICACIÓN DE ESTRUCTURA" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$PROJECT_DIR = "C:\Users\Admin\Documents\PPP\app_cinco"
$items = @(
    @{Path="backend"; Name="Backend"},
    @{Path="frontend"; Name="Frontend"},
    @{Path="env"; Name="Entorno virtual"},
    @{Path="backend\requirements.txt"; Name="Requirements.txt"},
    @{Path="frontend\package.json"; Name="Package.json"},
    @{Path="backend\.env.example"; Name=".env.example (backend)"},
    @{Path="frontend\.env.local.example"; Name=".env.local.example (frontend)"}
)

foreach ($item in $items) {
    $fullPath = Join-Path $PROJECT_DIR $item.Path
    Write-Host "[$($item.Name)]" -NoNewline
    if (Test-Path $fullPath) {
        Write-Host " OK" -ForegroundColor Green
    } else {
        Write-Host " FAIL - No encontrado" -ForegroundColor Red
    }
}

Write-Host ""
Start-Sleep -Seconds 2

# ========== FASE 3: PRUEBA BACKEND ==========
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "FASE 3: PRUEBA BACKEND" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$originalLocation = Get-Location
Set-Location (Join-Path $PROJECT_DIR "backend")

& "$PROJECT_DIR\env\Scripts\Activate.ps1"

Write-Host "[Django Check] Ejecutando python manage.py check..." -ForegroundColor Cyan
$checkResult = & python manage.py check 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK - Configuracion de Django" -ForegroundColor Green
} else {
    Write-Host " FAIL - Errores en configuracion:" -ForegroundColor Red
    Write-Host $checkResult -ForegroundColor Red
}

Write-Host ""
Write-Host "[Migraciones] Verificando estado..." -ForegroundColor Cyan
$migrations = & python manage.py showmigrations 2>&1
Write-Host " OK - Migraciones listadas" -ForegroundColor Green

Write-Host ""
Start-Sleep -Seconds 2

# ========== FASE 4: PRUEBA FRONTEND ==========
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "FASE 4: PRUEBA FRONTEND" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

Set-Location (Join-Path $PROJECT_DIR "frontend")

Write-Host "[Dependencias]" -ForegroundColor Cyan
if (Test-Path "node_modules") {
    $moduleCount = (Get-ChildItem "node_modules" -Directory -ErrorAction SilentlyContinue).Count
    Write-Host " OK - node_modules existe ($moduleCount paquetes)" -ForegroundColor Green
} else {
    Write-Host " WARN - node_modules no existe - ejecutar 'npm install'" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[Linting] Ejecutando npm run lint..." -ForegroundColor Cyan
$lintResult = npm run lint 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK - Linting" -ForegroundColor Green
} else {
    Write-Host " WARN - Revisar warnings/errors de linting" -ForegroundColor Yellow
}

Write-Host ""
Start-Sleep -Seconds 2

# ========== FASE 5: HEALTH CHECKS ==========
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "FASE 5: HEALTH CHECKS" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

Write-Host "[Backend Health Check] http://127.0.0.1:8000/auth/health/" -ForegroundColor Cyan
try {
    $backendHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/health/" -Method Get -TimeoutSec 5
    Write-Host " OK - Backend respondiendo" -ForegroundColor Green
    Write-Host "   Status: $($backendHealth.status)" -ForegroundColor Cyan
    Write-Host "   BD Default: $($backendHealth.databases.default)" -ForegroundColor Cyan
    Write-Host "   BD Azul: $($backendHealth.databases.azul)" -ForegroundColor Cyan
} catch {
    Write-Host " FAIL - Backend no disponible" -ForegroundColor Red
    Write-Host "   Asegurate de que el servidor este corriendo:" -ForegroundColor Yellow
    Write-Host "   cd backend; python manage.py runserver" -ForegroundColor Gray
}

Write-Host ""
Write-Host "[Frontend Health Check] http://localhost:3000" -ForegroundColor Cyan
try {
    $frontendHealth = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($frontendHealth.StatusCode -eq 200) {
        Write-Host " OK - Frontend respondiendo" -ForegroundColor Green
    }
} catch {
    Write-Host " FAIL - Frontend no disponible" -ForegroundColor Red
    Write-Host "   Asegurate de que el servidor este corriendo:" -ForegroundColor Yellow
    Write-Host "   cd frontend; npm run dev" -ForegroundColor Gray
}

Write-Host ""
Start-Sleep -Seconds 2

# ========== RESUMEN FINAL ==========
Set-Location $originalLocation

$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "RESUMEN DE PRUEBAS" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Tiempo total: $($duration.TotalSeconds) segundos" -ForegroundColor Cyan
Write-Host ""
Write-Host "[Siguiente paso]:" -ForegroundColor Yellow
Write-Host "   1. Revisa los resultados anteriores" -ForegroundColor White
Write-Host "   2. Corrige cualquier error encontrado" -ForegroundColor White
Write-Host "   3. Asegúrate de que ambos servidores estén corriendo" -ForegroundColor White
Write-Host "   4. Consulta MANUAL_TESTING.md para pruebas detalladas" -ForegroundColor White
Write-Host ""
Write-Host "[Para iniciar los servidores]:" -ForegroundColor Yellow
Write-Host "   Backend:  cd backend; python manage.py runserver" -ForegroundColor Gray
Write-Host "   Frontend: cd frontend; npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "[Documentacion]:" -ForegroundColor Yellow
Write-Host "   - README.md: Guía completa de CI/CD" -ForegroundColor Gray
Write-Host "   - MANUAL_TESTING.md: Guía de pruebas manuales" -ForegroundColor Gray
Write-Host "   - DEPLOYMENT.md: Guía rápida de deployment" -ForegroundColor Gray
Write-Host ""
