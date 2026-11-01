param([ValidateSet('center','left_near_b060','right_inter_m080','right_open_m100','right_corner_m140')][string]$Accion='center',
      [ValidateSet('apartado','centro')][string]$Ubicacion='centro',
      [ValidateSet('behind','execution','overview','goal','follow')][string]$Camara='goal',
      [string]$Referencia,[string]$Salida,[switch]$Viewer,[switch]$Capturas,
      [string]$Python,[string]$PolicyPython,[string]$DeployPath,[string]$LocoDeployPath)
$ErrorActionPreference='Stop'
$bundle=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. "$PSScriptRoot/_experiment_paths.ps1"
$paths=Resolve-ExperimentPaths -Bundle $bundle -Python $Python -PolicyPython $PolicyPython -DeployPath $DeployPath -LocoDeployPath $LocoDeployPath
$python=$paths.Python
$policy=$paths.PolicyPython
$deploy=$paths.DeployPath
$loco=$paths.LocoDeployPath
if (-not $Salida) { $Salida=Join-Path $bundle ('validation/passive_coverage_h3b/'+$Accion+'_'+$Ubicacion+'_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
$placement=@{'apartado'='aside';'centro'='center'}[$Ubicacion]
$arguments=@('-X','utf8','-u','-B','-m','experiments.passive_coverage_h3b.run',
    '--deploy',$deploy,'--loco-deploy',$loco,'--policy-python',$policy,'--output',([IO.Path]::GetFullPath($Salida)),
    '--placement',$placement,'--action',$Accion,'--camera',$Camara)
if ($Referencia) { $arguments+=@('--reference',(Resolve-Path -LiteralPath $Referencia).Path) }
if ($Viewer) { $arguments+='--viewer' }; if ($Capturas) { $arguments+='--capture' }
Push-Location -LiteralPath (Join-Path $bundle 'app/RoboPenalty')
try { & $python @arguments; $code=$LASTEXITCODE } finally { Pop-Location }
exit $code
