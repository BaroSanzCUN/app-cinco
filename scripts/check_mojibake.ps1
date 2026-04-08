param(
    [string[]]$Targets = @("backend", "frontend")
)

$ErrorActionPreference = "Stop"

$args = @(
    "-n",
    "--hidden",
    "--glob", "!**/.git/**",
    "--glob", "!**/.next/**",
    "--glob", "!**/node_modules/**",
    "--glob", "!**/__pycache__/**",
    "--glob", "!**/.venv/**",
    "--glob", "!**/env/**",
    "--glob", "!**/env_py314_backup/**",
    "(Ã.|Â.|ðŸ|�)"
)
$args += $Targets

$output = & rg @args
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "[ERROR] Se detectaron posibles textos corruptos (mojibake):" -ForegroundColor Red
    Write-Output $output
    exit 1
}

if ($exitCode -eq 1) {
    Write-Host "[OK] No se detecto mojibake en los targets analizados." -ForegroundColor Green
    exit 0
}

Write-Host "[ERROR] Fallo la ejecucion de rg para validar mojibake." -ForegroundColor Red
exit 2
