param([string]$Python, [switch]$SoloRecursos, [string]$DeployPath)
. "$PSScriptRoot/_common.ps1"
$exe = Get-BundlePython -Python $Python
& $exe -E -s -B -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) and sys.maxsize > 2**32 else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Se requiere CPython 3.12 x64.' }

$bundle = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$app = Join-Path $bundle 'app/RoboPenalty'
Push-Location -LiteralPath $app
try {
    & $exe -X utf8 -E -s -B -m portability.install_resources
    $resourceCode = $LASTEXITCODE
} finally { Pop-Location }
if ($resourceCode -ne 0 -and $resourceCode -ne 2) { throw 'Fallo de descarga/integridad; no se continuara.' }
if ($DeployPath) {
    & "$PSScriptRoot/importar_deploy.ps1" -DeployPath $DeployPath -Python $exe
    if ($LASTEXITCODE -ne 0) { throw 'Deploy no compatible. No se habilito la simulacion.' }
}
if ($SoloRecursos) {
    & "$PSScriptRoot/verificar.ps1" -Python $exe -ResourcesOnly
    if ($LASTEXITCODE -eq 0) { exit 0 }
    exit 2
}

# Preparing core packages is independent of the still-disabled resource steps.
$venv = Join-Path $bundle '.venv'
if (-not (Test-Path -LiteralPath $venv)) {
    & $exe -E -s -B -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la creacion del entorno virtual.' }
}
$localPython = Join-Path $venv 'Scripts/python.exe'
$requirements = Join-Path $bundle 'app/RoboPenalty/requirements-windows.txt'
& $localPython -I -m pip --isolated --disable-pip-version-check install --no-cache-dir --index-url https://pypi.org/simple -r $requirements
if ($LASTEXITCODE -ne 0) { throw 'Fallo pip; no se continuara.' }
& "$PSScriptRoot/verificar.ps1" -Python $localPython
$checkCode = $LASTEXITCODE
if ($checkCode -eq 0) {
    Write-Output 'Instalacion local completa: 104/104 recursos exactos. Los permisos de redistribucion siguen siendo independientes.'
    exit 0
}
if ($resourceCode -eq 2) {
    # Do not mask unrelated package, platform or integrity failures as a partial success.
    Push-Location -LiteralPath $app
    try {
        $detailLines = & $localPython -X utf8 -E -s -B -m portability.diagnose --json
        $details = ($detailLines -join "`n") | ConvertFrom-Json
    } finally { Pop-Location }
    if (-not $details.python.ready -or -not $details.inventory.ready -or -not $details.platform_supported) {
        throw 'Hay errores tecnicos adicionales a los permisos pendientes; revisar el diagnostico.'
    }
    $pendingTargets = @($details.licensing.resources | ForEach-Object { $_.target })
    $problems = @($details.external.problems)
    if ($problems.Count -ne $pendingTargets.Count) { throw 'El conjunto de faltantes no coincide con los pasos pendientes.' }
    foreach ($problem in $problems) {
        if ($problem.kind -ne 'missing' -or $pendingTargets -notcontains $problem.resource) {
            throw 'Diferencia de integridad no explicada por los pasos pendientes.'
        }
    }
    Write-Output 'Entorno core preparado. Instalacion PARCIAL: 26 pasos de recursos pendientes; partida bloqueada. No se habilitaron permisos por aceptacion de una bandera.'
    exit 2
}
exit $checkCode
