param([ValidateSet('left_near_b060','center')][string]$Accion='left_near_b060',
      [ValidateSet('active','passive')][string]$Modo='active',[double]$Amplitud=0.04,
      [ValidateSet('goal','behind','execution','overview')][string]$Camara='goal',
      [string]$Salida,[switch]$Viewer,
      [string]$Python,[string]$PolicyPython,[string]$DeployPath,[string]$LocoDeployPath,[string]$Referencia)
$ErrorActionPreference='Stop'
if ($Amplitud -notin @(0.04,0.08)) { throw 'Amplitud fuera del protocolo experimental.' }
$bundle=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. "$PSScriptRoot/_experiment_paths.ps1"
$paths=Resolve-ExperimentPaths -Bundle $bundle -Python $Python -PolicyPython $PolicyPython -DeployPath $DeployPath -LocoDeployPath $LocoDeployPath
$python=$paths.Python
$policy=$paths.PolicyPython
$deploy=$paths.DeployPath
$loco=$paths.LocoDeployPath
if (-not $Referencia) { $Referencia=Join-Path $bundle ('validation/passive_coverage_h3b/reference_'+$Accion+'/interception.json') }
$reference=(Resolve-Path -LiteralPath $Referencia).Path
if (-not $Salida) { $Salida=Join-Path $bundle ('validation/low_block_h3c/'+$Modo+'_'+$Accion+'_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff')) }
$amp=$Amplitud.ToString([Globalization.CultureInfo]::InvariantCulture)
$arguments=@('-X','utf8','-u','-B','-m','experiments.low_block_h3c.run','--deploy',$deploy,'--loco-deploy',$loco,
    '--policy-python',$policy,'--reference',$reference,'--output',([IO.Path]::GetFullPath($Salida)),
    '--action',$Accion,'--mode',$Modo,'--amplitude',$amp,'--camera',$Camara)
if ($Viewer) { $arguments+='--viewer' }
Push-Location -LiteralPath (Join-Path $bundle 'app/RoboPenalty')
try { & $python @arguments; $code=$LASTEXITCODE } finally { Pop-Location }
exit $code
