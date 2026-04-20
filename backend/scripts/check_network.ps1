param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-EnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $map
    }

    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line) { return }
        if ($line.StartsWith("#")) { return }
        $eqIndex = $line.IndexOf("=")
        if ($eqIndex -lt 1) { return }

        $key = $line.Substring(0, $eqIndex).Trim()
        $value = $line.Substring($eqIndex + 1).Trim().Trim('"').Trim("'")
        $map[$key] = $value
    }

    return $map
}

function Merge-Maps {
    param(
        [hashtable]$Base,
        [hashtable]$Override
    )

    $merged = @{}
    foreach ($k in $Base.Keys) {
        $merged[$k] = $Base[$k]
    }
    foreach ($k in $Override.Keys) {
        $merged[$k] = $Override[$k]
    }
    return $merged
}

function Test-Port {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HostName,
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    try {
        $result = Test-NetConnection -ComputerName $HostName -Port $Port -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
        return [bool]$result.TcpTestSucceeded
    }
    catch {
        return $false
    }
}

function Is-PrivateHost {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HostName
    )

    if ($HostName -eq "localhost" -or $HostName -eq "127.0.0.1") {
        return $false
    }

    return $HostName -match "^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)"
}

$backendRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$envPath = Join-Path $backendRoot ".env"
$envLocalPath = Join-Path $backendRoot ".env.local"

$envBase = Read-EnvFile -Path $envPath
$envLocal = Read-EnvFile -Path $envLocalPath
$cfg = Merge-Maps -Base $envBase -Override $envLocal

$bdHost = if ($cfg.ContainsKey("BD_HOST")) { $cfg["BD_HOST"] } else { "127.0.0.1" }
$bdPort = if ($cfg.ContainsKey("BD_PORT")) { [int]$cfg["BD_PORT"] } else { 3306 }
$azulHost = if ($cfg.ContainsKey("DB_AZUL_HOST")) { $cfg["DB_AZUL_HOST"] } else { "127.0.0.1" }
$azulPort = if ($cfg.ContainsKey("DB_AZUL_PORT")) { [int]$cfg["DB_AZUL_PORT"] } else { 3306 }

$bdOk = Test-Port -HostName $bdHost -Port $bdPort
$azulOk = Test-Port -HostName $azulHost -Port $azulPort
$apiOk = Test-Port -HostName "127.0.0.1" -Port 8000

Write-Host ""
Write-Host "=== Diagnostico de red (backend) ==="
Write-Host "Fuente de variables: .env + .env.local (con prioridad en .env.local)"
Write-Host ""
Write-Host ("DB default: {0}:{1} -> {2}" -f $bdHost, $bdPort, ($(if ($bdOk) { "OK" } else { "FAIL" })))
Write-Host ("DB azul   : {0}:{1} -> {2}" -f $azulHost, $azulPort, ($(if ($azulOk) { "OK" } else { "FAIL" })))
Write-Host ("API local : 127.0.0.1:8000 -> {0}" -f ($(if ($apiOk) { "UP" } else { "DOWN" })))
Write-Host ""

$vpnHintNeeded = ((Is-PrivateHost -HostName $bdHost) -or (Is-PrivateHost -HostName $azulHost))
if ($vpnHintNeeded) {
    Write-Host "NOTA IMPORTANTE: Para conexion local hacia BD de red privada, es necesario activar la VPN."
    Write-Host "Si la VPN no esta activa, el backend no inicia y el login puede fallar con ERR_CONNECTION_REFUSED."
    Write-Host ""
}

if (-not $bdOk -or -not $azulOk) {
    Write-Host "RESULTADO: Hay fallo de conectividad a base de datos."
    exit 1
}

if (-not $apiOk) {
    Write-Host "RESULTADO: BD OK, pero el backend aun no esta levantado en 127.0.0.1:8000."
    Write-Host "Inicia con: .\\.venv\\Scripts\\python.exe manage.py runserver 127.0.0.1:8000"
    exit 2
}

Write-Host "RESULTADO: Conectividad correcta (BD + API local)."
exit 0
