param([Parameter(Mandatory=$true)][string]$DeployPath,
      [string]$Python, [switch]$Viewer, [string]$Validacion, [string]$Salida)
$ErrorActionPreference = 'Stop'
$bundle = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $Python) { $Python = Join-Path $bundle 'validation/keeper_balance4b/.venv/Scripts/python.exe' }
$Python = (Resolve-Path -LiteralPath $Python).Path
$deploy = (Resolve-Path -LiteralPath $DeployPath).Path
if (-not $Salida) { $Salida = Join-Path $bundle ('validation/keeper_residual4b2/run_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
$Salida = [IO.Path]::GetFullPath($Salida)
$arguments = @('-X','utf8','-E','-s','-B','-m','experiments.keeper_residual4b2.run',
               '--deploy',$deploy,'--output',$Salida)
if ($Viewer) {
    if (-not $Validacion) { throw 'Indique -Validacion con una ejecucion headless de 4B.2 aprobada. No basta con que el robot permanezca de pie.' }
    $arguments += @('--viewer','--validated-run',(Resolve-Path -LiteralPath $Validacion).Path)
}
Push-Location -LiteralPath (Join-Path $bundle 'app/RoboPenalty')
try { & $Python @arguments; $code = $LASTEXITCODE } finally { Pop-Location }
exit $code
