param([string]$Python, [switch]$SoloRecursos, [string]$DeployPath,
      [switch]$Interactivo, [switch]$NoInteractivo)
. "$PSScriptRoot/_common.ps1"
. "$PSScriptRoot/_install_input.ps1"
$ask = Resolve-InstallInteraction -Interactivo:$Interactivo -NoInteractivo:$NoInteractivo
if ($PSVersionTable.PSVersion -lt [version]'5.1') { throw 'Se requiere PowerShell 5.1 o posterior.' }
$exe = Get-BundlePython -Python $Python
& $exe -E -s -B -c "import os,sys; print('Python',sys.version.split()[0]); raise SystemExit(0 if os.name == 'nt' and sys.version_info[:2] == (3,12) and sys.maxsize > 2**32 else 1)"
if ($LASTEXITCODE -ne 0) { throw 'Se requiere Windows y CPython 3.12 x64. Ver docs/INSTALACION_WINDOWS.md.' }

$bundle = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$app = Join-Path $bundle 'app/RoboPenalty'
Push-Location -LiteralPath $app
try {
    $downloadLines = & $exe -X utf8 -E -s -B -m portability.install_resources --json
    $resourceCode = $LASTEXITCODE
} finally { Pop-Location }
if ($resourceCode -ne 0 -and $resourceCode -ne 2) {
    $downloadLines | Write-Output
    throw 'Fallo de descarga/integridad; no se continuara. Revisar conexion y SHA-256.'
}
$downloads = ($downloadLines -join "`n") | ConvertFrom-Json
Write-Host "Pasos autorizados comprobados: $(@($downloads.resources).Count). Descargas pendientes NO habilitadas: $(@($downloads.blocked).Count)."
$state = Get-InstallResourceState -Executable $exe -App $app
if (-not $state.inventory.ready) { throw 'El inventario del paquete no coincide; usar una copia integra del proyecto.' }
$correct = @($state.external.files | Where-Object { $_.status -eq 'ok' }).Count
Write-Host "Recursos correctos antes de importar: $correct/104."
$DeployPath = Get-InstallDeployFolder -ExplicitPath $DeployPath -Needed (-not $state.resource_execution_ready) -Ask $ask
if ($DeployPath) {
    & "$PSScriptRoot/importar_deploy.ps1" -DeployPath $DeployPath -Python $exe
    if ($LASTEXITCODE -ne 0) { throw 'Deploy no compatible. No se habilito la simulacion.' }
}
if ($SoloRecursos) {
    $state = Get-InstallResourceState -Executable $exe -App $app
    if ($state.resource_execution_ready) { Write-Output '104/104 recursos exactos. Falta comprobar los paquetes Python antes de jugar.'; exit 0 }
    if ($state.inventory.ready -and (Test-OnlyExpectedDeployMissing -Details $state)) {
        Write-Output 'PARCIAL: 78/104. Obtener legitimamente Deploy adaptado compatible y repetir con -DeployPath. Ver docs/INSTALACION_WINDOWS.md.'
        exit 2
    }
    throw 'Hay errores de integridad o recursos distintos de los 26 faltantes esperados; ejecutar verificar.ps1 -ResourcesOnly.'
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
    $details = Get-InstallResourceState -Executable $localPython -App $app -Full
    if (-not $details.python.ready -or -not $details.inventory.ready -or -not $details.platform_supported) {
        throw 'Hay errores tecnicos adicionales a los permisos pendientes; revisar el diagnostico.'
    }
    if (-not (Test-OnlyExpectedDeployMissing -Details $details)) { throw 'El conjunto de errores no coincide con los 26 recursos Deploy faltantes.' }
    Write-Output 'Entorno Python preparado. INSTALACION PARCIAL: 78/104 recursos; NO se puede jugar. No hubo descarga de Deploy.'
    Write-Output 'Siguiente paso: obtener legitimamente la copia adaptada compatible y repetir instalar.ps1 -DeployPath <carpeta>. Guia: docs/INSTALACION_WINDOWS.md.'
    exit 2
}
exit $checkCode
