Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-BundlePython {
    param([string]$Python)
    if ($Python) {
        if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
            throw 'La ruta -Python no existe. Indicar un ejecutable Python real.'
        }
        return (Resolve-Path -LiteralPath $Python).Path
    }
    $localPython = Join-Path $PSScriptRoot '../.venv/Scripts/python.exe'
    if (Test-Path -LiteralPath $localPython -PathType Leaf) {
        return (Resolve-Path -LiteralPath $localPython).Path
    }
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        $candidate = & $launcher.Source -3.12 -c 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) { return [string]$candidate }
    }
    throw 'No existe .venv ni Python 3.12 en py. Usar -Python con la ruta real de CPython 3.12. No se buscan entornos de otros proyectos.'
}
