param([ValidateSet('baseline','transfer')][string]$Modo='baseline',[switch]$Viewer,[string]$Salida,
      [string]$Python,[string]$PolicyPython,[string]$DeployPath,[string]$LocoDeployPath)
$ErrorActionPreference='Stop'
$bundle=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. "$PSScriptRoot/_experiment_paths.ps1"
$paths=Resolve-ExperimentPaths -Bundle $bundle -Python $Python -PolicyPython $PolicyPython -DeployPath $DeployPath -LocoDeployPath $LocoDeployPath
$python=$paths.Python
$policy=$paths.PolicyPython
$deploy=$paths.DeployPath
$loco=$paths.LocoDeployPath
if (-not $Salida) { $Salida=Join-Path $bundle ('validation/weight_transfer_h3d/'+$Modo+'_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
$argsList=@('-X','utf8','-u','-B','-m','experiments.weight_transfer_h3d.run','--deploy',$deploy,'--loco-deploy',$loco,
    '--policy-python',$policy,'--output',([IO.Path]::GetFullPath($Salida)),'--mode',$Modo)
if ($Viewer) { $argsList+='--viewer' }
Push-Location -LiteralPath (Join-Path $bundle 'app/RoboPenalty')
try { & $python @argsList; $code=$LASTEXITCODE } finally { Pop-Location }
exit $code
