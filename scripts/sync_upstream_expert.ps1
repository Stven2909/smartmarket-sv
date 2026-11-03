# Sincroniza de forma segura el fork con la rama Python del equipo.
# Por defecto solo comprueba el avance; para publicar usa -Apply.
# Nunca escribe en develop, main del equipo, backend-laravel ni frontend-react.
[CmdletBinding()]
param(
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$upstreamUrl = "https://github.com/Stven2909/smartmarket-sv.git"
$upstreamBranch = "expert-system-python"
$forkBranchRef = "refs/remotes/origin/main"
$upstreamTrackingRef = "refs/remotes/sync-check/expert-system-python"
$destinationRef = "refs/heads/expert-system-python"

function Invoke-CheckedGit {
    param([Parameter(Mandatory = $true)][string[]]$GitArgs)
    & git -C $repoRoot @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw ("Error en git: " + ($GitArgs -join " "))
    }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Se requiere Git instalado y disponible en PATH."
}
if (-not (Test-Path (Join-Path $repoRoot ".git"))) {
    throw "Ejecuta este script desde un clon Git del repositorio del sistema experto."
}

$originUrl = (& git -C $repoRoot remote get-url origin | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $originUrl -notmatch '^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)HenryBo06/Sistema-experto-fork(\.git)?/?$') {
    throw "El remoto origin debe corresponder exactamente a HenryBo06/Sistema-experto-fork. Recibido: $originUrl"
}

Write-Host "Consultando las ramas del fork y del equipo (solo lectura)..."
Invoke-CheckedGit -GitArgs @("fetch", "--quiet", "--no-tags", "origin", ("+refs/heads/main:" + $forkBranchRef))
Invoke-CheckedGit -GitArgs @("fetch", "--quiet", "--no-tags", $upstreamUrl, ("+refs/heads/" + $upstreamBranch + ":" + $upstreamTrackingRef))

$forkHead = (& git -C $repoRoot rev-parse $forkBranchRef | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw "No se pudo resolver origin/main." }
$upstreamHead = (& git -C $repoRoot rev-parse $upstreamTrackingRef | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw "No se pudo resolver expert-system-python." }

Write-Host "Fork main:            $forkHead"
Write-Host "Equipo expert-python: $upstreamHead"

if ($forkHead -eq $upstreamHead) {
    Write-Host "Las ramas ya estan sincronizadas. No hay cambios pendientes."
    exit 0
}

& git -C $repoRoot merge-base --is-ancestor $upstreamHead $forkHead
if ($LASTEXITCODE -ne 0) {
    throw "Se detecto divergencia: el commit del equipo NO es ancestro del fork. No se realiza push. Revisar e integrar manualmente los commits del equipo."
}

$ahead = (& git -C $repoRoot rev-list --count "$upstreamHead..$forkHead" | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw "No se pudo calcular la diferencia de commits." }
Write-Host "Sincronizacion posible por fast-forward: $ahead commits por transferir."
Write-Host "Rama destino unica: Stven2909/smartmarket-sv:$upstreamBranch"

if (-not $Apply) {
    Write-Host "Modo comprobacion: no se ha publicado nada."
    Write-Host "Cuando hayas revisado el resultado, ejecuta el mismo script con -Apply."
    exit 0
}

Write-Host "Publicando exclusivamente en expert-system-python, sin --force..."
# Git rechaza un push no fast-forward si alguien cambia la rama mientras tanto.
Invoke-CheckedGit -GitArgs @("push", "--porcelain", $upstreamUrl, ($forkBranchRef + ":" + $destinationRef))
Write-Host "Push aceptado. Comprueba las pruebas de GitHub Actions del repositorio del equipo."
