# Script de prueba manual - Deploy Backend Local
# Este script simula el proceso de deployment en Windows

Write-Host "=== 🧪 Prueba Manual de Deploy Backend ===" -ForegroundColor Cyan
Write-Host ""

$PROJECT_DIR = "C:\Users\Admin\Documents\PPP\app_cinco"
$BACKEND_DIR = "$PROJECT_DIR\backend"
$ENV_DIR = "$PROJECT_DIR\env"

# 1. Verificar que estamos en el directorio correcto
Write-Host "📂 Verificando directorio..." -ForegroundColor Yellow
if (Test-Path $PROJECT_DIR) {
    Write-Host "✅ Directorio encontrado: $PROJECT_DIR" -ForegroundColor Green
} else {
    Write-Host "❌ Error: Directorio no encontrado" -ForegroundColor Red
    exit 1
}

# 2. Verificar Python
Write-Host ""
Write-Host "🐍 Verificando Python..." -ForegroundColor Yellow
& python --version
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Python encontrado" -ForegroundColor Green
} else {
    Write-Host "❌ Error: Python no encontrado" -ForegroundColor Red
    exit 1
}

# 3. Activar entorno virtual
Write-Host ""
Write-Host "🔧 Activando entorno virtual..." -ForegroundColor Yellow
& "$ENV_DIR\Scripts\Activate.ps1"

# 4. Instalar/actualizar dependencias
Write-Host ""
Write-Host "📚 Verificando dependencias..." -ForegroundColor Yellow
Set-Location $BACKEND_DIR
pip list | Select-String "Django"

# 5. Verificar configuración
Write-Host ""
Write-Host "🔍 Verificando configuración de Django..." -ForegroundColor Yellow
& python manage.py check
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Configuración correcta" -ForegroundColor Green
} else {
    Write-Host "❌ Error en configuración" -ForegroundColor Red
    exit 1
}

# 6. Ver migraciones pendientes
Write-Host ""
Write-Host "🗄️ Verificando migraciones..." -ForegroundColor Yellow
& python manage.py showmigrations --database=default | Select-String "\[ \]" | Measure-Object | ForEach-Object { $_.Count }
Write-Host "Migraciones pendientes (default): $($_.Count)" -ForegroundColor Cyan

# 7. Collectstatic (simulado)
Write-Host ""
Write-Host "📁 Verificando archivos estáticos..." -ForegroundColor Yellow
if (Test-Path "$BACKEND_DIR\static") {
    Write-Host "✅ Directorio static existe" -ForegroundColor Green
} else {
    Write-Host "⚠️ Crear directorio static si es necesario" -ForegroundColor Yellow
}

# 8. Health check
Write-Host ""
Write-Host "🏥 Probando health check..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/auth/health/" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Health check respondió correctamente" -ForegroundColor Green
        Write-Host $response.Content -ForegroundColor Cyan
    }
} catch {
    Write-Host "⚠️ Health check no disponible (¿servidor corriendo?)" -ForegroundColor Yellow
    Write-Host "Inicia el servidor con: python manage.py runserver" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== ✅ Prueba de Deploy Completada ===" -ForegroundColor Green
Write-Host ""
Write-Host "Siguiente paso: Iniciar servidor con 'python manage.py runserver'" -ForegroundColor Cyan
Write-Host "Luego probar: http://127.0.0.1:8000/auth/health/" -ForegroundColor Cyan
