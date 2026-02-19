# Script de prueba manual - Deploy Frontend Local
# Este script simula el proceso de deployment en Windows

Write-Host "=== 🧪 Prueba Manual de Deploy Frontend ===" -ForegroundColor Cyan
Write-Host ""

$PROJECT_DIR = "C:\Users\Admin\Documents\PPP\app_cinco"
$FRONTEND_DIR = "$PROJECT_DIR\frontend"

# 1. Verificar directorio
Write-Host "📂 Verificando directorio..." -ForegroundColor Yellow
if (Test-Path $FRONTEND_DIR) {
    Write-Host "✅ Directorio encontrado: $FRONTEND_DIR" -ForegroundColor Green
} else {
    Write-Host "❌ Error: Directorio no encontrado" -ForegroundColor Red
    exit 1
}

# 2. Verificar Node.js
Write-Host ""
Write-Host "📦 Verificando Node.js..." -ForegroundColor Yellow
& node --version
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Node.js encontrado" -ForegroundColor Green
} else {
    Write-Host "❌ Error: Node.js no encontrado" -ForegroundColor Red
    exit 1
}

# 3. Verificar npm
Write-Host ""
Write-Host "📦 Verificando npm..." -ForegroundColor Yellow
& npm --version
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ npm encontrado" -ForegroundColor Green
} else {
    Write-Host "❌ Error: npm no encontrado" -ForegroundColor Red
    exit 1
}

# 4. Verificar package.json
Write-Host ""
Write-Host "📄 Verificando package.json..." -ForegroundColor Yellow
Set-Location $FRONTEND_DIR
if (Test-Path "package.json") {
    Write-Host "✅ package.json encontrado" -ForegroundColor Green
    Get-Content package.json | Select-String '"name":' | ForEach-Object { Write-Host $_ -ForegroundColor Cyan }
} else {
    Write-Host "❌ Error: package.json no encontrado" -ForegroundColor Red
    exit 1
}

# 5. Verificar node_modules
Write-Host ""
Write-Host "📚 Verificando dependencias..." -ForegroundColor Yellow
if (Test-Path "node_modules") {
    $moduleCount = (Get-ChildItem "node_modules" -Directory).Count
    Write-Host "✅ node_modules existe ($moduleCount paquetes)" -ForegroundColor Green
} else {
    Write-Host "⚠️ node_modules no existe - ejecutar 'npm install'" -ForegroundColor Yellow
}

# 6. Verificar .next (build)
Write-Host ""
Write-Host "🏗️ Verificando build..." -ForegroundColor Yellow
if (Test-Path ".next") {
    Write-Host "✅ Build de Next.js existe" -ForegroundColor Green
} else {
    Write-Host "⚠️ Build no existe - ejecutar 'npm run build'" -ForegroundColor Yellow
}

# 7. Verificar variables de entorno
Write-Host ""
Write-Host "🔐 Verificando variables de entorno..." -ForegroundColor Yellow
if (Test-Path ".env.local") {
    Write-Host "✅ .env.local encontrado" -ForegroundColor Green
} else {
    Write-Host "⚠️ .env.local no existe - crear desde .env.local.example" -ForegroundColor Yellow
}

# 8. Health check (frontend)
Write-Host ""
Write-Host "🏥 Probando frontend..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Frontend respondió correctamente" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ Frontend no disponible (¿servidor corriendo?)" -ForegroundColor Yellow
    Write-Host "Inicia el servidor con: npm run dev" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== ✅ Prueba de Deploy Completada ===" -ForegroundColor Green
Write-Host ""
Write-Host "Siguiente paso: Iniciar servidor con 'npm run dev'" -ForegroundColor Cyan
Write-Host "Luego probar: http://localhost:3000" -ForegroundColor Cyan
