param([ValidateSet('original','fast','fast_v1','fast_v2')][string]$Variante='original',
      [ValidateSet('LEFT','RIGHT')][string]$Lado='LEFT',
      [ValidateSet('full','legs_torso','arms')][string]$Componente='full',
      [switch]$Viewer,[switch]$Capturas,[string]$Salida,
      [string]$Python,[string]$PolicyPython,[string]$DeployPath,[string]$LocoDeployPath)
$ErrorActionPreference='Stop'
$bundle=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. "$PSScriptRoot/_experiment_paths.ps1"
$paths=Resolve-ExperimentPaths -Bundle $bundle -Python $Python -PolicyPython $PolicyPython -DeployPath $DeployPath -LocoDeployPath $LocoDeployPath
$python=$paths.Python
$policy=$paths.PolicyPython
$deploy=$paths.DeployPath
$loco=$paths.LocoDeployPath
if (-not $Salida) { $Salida=Join-Path $bundle ('validation/keeper_center_h25/'+$Variante+'_'+$Lado+'_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
$arguments=@('-X','utf8','-u','-B','-m','experiments.keeper_center_h25.run',
    '--deploy',$deploy,'--loco-deploy',$loco,'--policy-python',$policy,'--output',([IO.Path]::GetFullPath($Salida)),
    '--variant',$Variante,'--side',$Lado,'--component',$Componente)
if ($Viewer) { $arguments+='--viewer' }; if ($Capturas) { $arguments+='--capture' }
Push-Location -LiteralPath (Join-Path $bundle 'app/RoboPenalty')
try { & $python @arguments; $code=$LASTEXITCODE } finally { Pop-Location }
exit $code
