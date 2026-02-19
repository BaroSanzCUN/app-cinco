# Test Manual de Deployment - App Cinco
# Version simplificada sin caracteres especiales

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host " PRUEBA MANUAL DE DEPLOYMENT" -ForegroundColor Cyan  
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_DIR = "C:\Users\Admin\Documents\PPP\app_cinco"

# Test 1: Backend Health Check
Write-Host "[TEST 1] Backend Health Check" -ForegroundColor Yellow
try {
    $result = Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/health/" -Method Get -TimeoutSec 5
    Write-Host " OK - Status: $($result.status)" -ForegroundColor Green
    Write-Host "   DB Default: $($result.databases.default)" -ForegroundColor Cyan
    Write-Host "   DB Azul: $($result.databases.azul)" -ForegroundColor Cyan
} catch {
    Write-Host " FAIL - Backend no disponible" -ForegroundColor Red
    Write-Host "   Ejecuta: cd backend; python manage.py runserver" -ForegroundColor Yellow
}

Write-Host ""

# Test 2: Frontend Health Check
Write-Host "[TEST 2] Frontend Health Check" -ForegroundColor Yellow
try {
    $result = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($result.StatusCode -eq 200) {
        Write-Host " OK - Frontend respondiendo" -ForegroundColor Green
    }
} catch {
    Write-Host " FAIL - Frontend no disponible" -ForegroundColor Red
    Write-Host "   Ejecuta: cd frontend; npm run dev" -ForegroundColor Yellow
}

Write-Host ""

# Test 3: Python Version
Write-Host "[TEST 3] Python Version" -ForegroundColor Yellow
$pyVersion = python --version 2>&1
Write-Host " $pyVersion" -ForegroundColor Cyan

Write-Host ""

# Test 4: Node Version
Write-Host "[TEST 4] Node Version" -ForegroundColor Yellow
$nodeVersion = node --version 2>&1
Write-Host " $nodeVersion" -ForegroundColor Cyan

Write-Host ""

# Test 5: Django Check
Write-Host "[TEST 5] Django Configuration" -ForegroundColor Yellow
Set-Location "$PROJECT_DIR\backend"
$checkResult = python manage.py check 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK - No errors" -ForegroundColor Green
} else {
    Write-Host " FAIL - See errors above" -ForegroundColor Red
}

Write-Host ""

# Test 6: Files Structure
Write-Host "[TEST 6] Project Structure" -ForegroundColor Yellow
Set-Location $PROJECT_DIR

$files = @(
    "backend\manage.py",
    "backend\requirements.txt",
    "frontend\package.json",
    "backend\.env.example",
    "frontend\.env.local.example",
    ".github\workflows\ci-cd.yml"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host " OK - $file" -ForegroundColor Green
    } else {
        Write-Host " MISS - $file" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host " PRUEBA COMPLETADA" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Documentacion disponible:" -ForegroundColor Yellow
Write-Host " - README.md (Guia completa CI/CD)" -ForegroundColor Gray
Write-Host " - MANUAL_TESTING.md (Guia de pruebas)" -ForegroundColor Gray
Write-Host " - DEPLOYMENT.md (Guia rapida)" -ForegroundColor Gray
Write-Host ""
