param([ValidateSet('Verificar','Headless','Visor')][string]$Modo = 'Verificar',
      [string]$Referencia, [string]$Python, [string]$Salida,
      [ValidateRange(1,100)][int]$Ensayos = 5, [int]$Semilla = 2810)
$ErrorActionPreference = 'Stop'
$bundle = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $Python) { $Python = Join-Path $bundle 'validation/keeper_reference4c/.venv-keeper-4c/Scripts/python.exe' }
$Python = (Resolve-Path -LiteralPath $Python).Path
if (-not $Referencia) { $Referencia = Join-Path $bundle '../G1-mjlab-soccer' }
$Referencia = (Resolve-Path -LiteralPath $Referencia).Path
$cache = Join-Path $bundle 'validation/keeper_reference4c/cache'
if (-not $Salida) { $Salida = Join-Path $bundle ('validation/keeper_reference4c/' + $Modo.ToLower() + '_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
$Salida = [IO.Path]::GetFullPath($Salida)
if ($Modo -eq 'Verificar') {
    if (Test-Path -LiteralPath $Salida) { throw 'La salida debe ser una carpeta nueva.' }
    New-Item -ItemType Directory -Path $Salida | Out-Null
    $arguments = @('-X','utf8','-u','-B','-m','experiments.keeper_reference4c.environment',
                   '--cache',$cache,'--output',(Join-Path $Salida 'environment.json'))
} else {
    $arguments = @('-X','utf8','-u','-B','-m','experiments.keeper_reference4c.observe_reference',
                   '--reference',$Referencia,'--cache',$cache,'--output',$Salida,
                   '--episodes',"$Ensayos",'--seed',"$Semilla")
    if ($Modo -eq 'Visor') { $arguments += '--viewer' }
}
Push-Location -LiteralPath (Join-Path $bundle 'app/RoboPenalty')
try { & $Python @arguments; $code = $LASTEXITCODE } finally { Pop-Location }
exit $code
