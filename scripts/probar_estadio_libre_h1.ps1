param([string]$Python,[string]$PolicyPython,[string]$DeployPath,[string]$LocoDeployPath,
      [ValidateSet('apartado','centro','sin-arquero')][string]$Ubicacion='apartado',
      [ValidateSet('behind','execution','overview','goal','follow')][string]$Camara='overview',
      [string]$Accion='right_inter_m080',[string]$Salida,[switch]$Viewer,[switch]$Capturas)
$ErrorActionPreference='Stop'
$bundle=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. "$PSScriptRoot/_experiment_paths.ps1"
$paths=Resolve-ExperimentPaths -Bundle $bundle -Python $Python -PolicyPython $PolicyPython -DeployPath $DeployPath -LocoDeployPath $LocoDeployPath
$Python=$paths.Python
$PolicyPython=$paths.PolicyPython
$DeployPath=$paths.DeployPath
$LocoDeployPath=$paths.LocoDeployPath
if (-not $Salida) { $Salida=Join-Path $bundle ('validation/free_keeper_stadium_h1/run_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
$Salida=[IO.Path]::GetFullPath($Salida)
$placement=@{'apartado'='aside';'centro'='center';'sin-arquero'='absent'}[$Ubicacion]
$parameters=@('-X','utf8','-u','-B','-m','experiments.free_keeper_stadium_h1.run',
    '--deploy',$DeployPath,'--loco-deploy',$LocoDeployPath,'--policy-python',$PolicyPython,
    '--placement',$placement,'--action',$Accion,'--camera',$Camara,'--output',$Salida)
if ($Viewer) { $parameters+='--viewer' }
if ($Capturas) { $parameters+='--capture' }
Push-Location -LiteralPath (Join-Path $bundle 'app/RoboPenalty')
try { & $Python @parameters; $code=$LASTEXITCODE } finally { Pop-Location }
exit $code
