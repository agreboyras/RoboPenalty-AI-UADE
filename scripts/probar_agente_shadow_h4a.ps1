param([ValidateSet('center','left_near_b060','right_inter_m080','right_open_m100','right_corner_m140')][string]$Accion='center',
      [ValidateSet('behind','execution','overview','goal','follow')][string]$Camara='goal',
      [string]$Salida,[switch]$Viewer,
      [string]$Python,[string]$PolicyPython,[string]$DeployPath,[string]$LocoDeployPath,[string]$Referencia,[string]$Baseline)
$ErrorActionPreference='Stop'
$bundle=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. "$PSScriptRoot/_experiment_paths.ps1"
$paths=Resolve-ExperimentPaths -Bundle $bundle -Python $Python -PolicyPython $PolicyPython -DeployPath $DeployPath -LocoDeployPath $LocoDeployPath
$python=$paths.Python
$policy=$paths.PolicyPython
$deploy=$paths.DeployPath
$loco=$paths.LocoDeployPath
$baselineName=if ($Accion -eq 'center') {'center_center'} elseif ($Accion -eq 'right_corner_m140') {'center_right_corner_m140_retry01'} else {'center_'+$Accion}
if (-not $Baseline) { $Baseline=Join-Path $bundle ('validation/passive_coverage_h3b/'+$baselineName) }
if (-not $Referencia) { $Referencia=Join-Path $bundle ('validation/passive_coverage_h3b/reference_'+$Accion+'/interception.json') }
$baseline=(Resolve-Path -LiteralPath $Baseline).Path
$reference=(Resolve-Path -LiteralPath $Referencia).Path
if (-not $Salida) { $Salida=Join-Path $bundle ('validation/shadow_agent_h4a/'+$Accion+'_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
$arguments=@('-X','utf8','-u','-B','-m','experiments.shadow_agent_h4a.run',
 '--deploy',$deploy,'--loco-deploy',$loco,'--policy-python',$policy,'--output',([IO.Path]::GetFullPath($Salida)),
 '--action',$Accion,'--camera',$Camara,'--baseline',$baseline,'--reference',$reference)
if ($Viewer) {$arguments+='--viewer'}
Push-Location -LiteralPath (Join-Path $bundle 'app/RoboPenalty')
try { & $python @arguments; $code=$LASTEXITCODE } finally { Pop-Location }
exit $code
