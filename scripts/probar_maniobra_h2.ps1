param([ValidateSet('equilibrio','transicion','maniobra')][string]$Ensayo='transicion',
      [ValidateSet('LEFT','RIGHT')][string]$Lado='LEFT',[switch]$Viewer,[switch]$Capturas,[string]$Salida,
      [string]$Python,[string]$PolicyPython,[string]$DeployPath,[string]$LocoDeployPath)
$ErrorActionPreference='Stop'
$bundle=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. "$PSScriptRoot/_experiment_paths.ps1"
$paths=Resolve-ExperimentPaths -Bundle $bundle -Python $Python -PolicyPython $PolicyPython -DeployPath $DeployPath -LocoDeployPath $LocoDeployPath
$python=$paths.Python
$policy=$paths.PolicyPython
$deploy=$paths.DeployPath
$loco=$paths.LocoDeployPath
if (-not $Salida) { $Salida=Join-Path $bundle ('validation/lateral_keeper_h2/'+$Ensayo+'_'+$Lado+'_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
$mode=@{'equilibrio'='balance';'transicion'='transfer';'maniobra'='maneuver'}[$Ensayo]
$arguments=@('-X','utf8','-u','-B','-m','experiments.lateral_keeper_h2.run',
    '--deploy',$deploy,'--loco-deploy',$loco,'--policy-python',$policy,
    '--output',([IO.Path]::GetFullPath($Salida)),'--mode',$mode,'--side',$Lado)
if ($Viewer) { $arguments+='--viewer' }
if ($Capturas) { $arguments+='--capture' }
Push-Location -LiteralPath (Join-Path $bundle 'app/RoboPenalty')
try { & $python @arguments; $code=$LASTEXITCODE } finally { Pop-Location }
exit $code
