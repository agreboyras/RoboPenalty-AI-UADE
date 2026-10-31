param([Parameter(Mandatory=$true)][string]$DeployPath,
      [string]$Python, [switch]$Viewer,
      [ValidateRange(1,100)][int]$Repeticiones = 3,
      [string]$Salida)
$ErrorActionPreference = 'Stop'
$bundle = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $Python) { $Python = Join-Path $bundle 'validation/keeper_balance4b/.venv/Scripts/python.exe' }
if (-not (Test-Path -LiteralPath $Python)) { throw 'Falta el entorno privado de 4B. Consulte la documentacion del experimento o indique -Python.' }
$Python = (Resolve-Path -LiteralPath $Python).Path
$deploy = (Resolve-Path -LiteralPath $DeployPath).Path
if (-not $Salida) { $Salida = Join-Path $bundle ('validation/keeper_balance4b/run_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
$Salida = [IO.Path]::GetFullPath($Salida)
$arguments = @('-X','utf8','-E','-s','-B','-m','experiments.free_keeper4b.run_trial',
               '--deploy',$deploy,'--output',$Salida,'--repeats',"$Repeticiones")
if ($Viewer) { $arguments += '--viewer' }
Push-Location -LiteralPath (Join-Path $bundle 'app/RoboPenalty')
try { & $Python @arguments; $code = $LASTEXITCODE } finally { Pop-Location }
exit $code
