param([ValidateSet('equilibrio','transicion','maniobra','maniobra_historica')][string]$Ensayo='transicion',
      [ValidateSet('LEFT','RIGHT')][string]$Lado='LEFT',[switch]$Viewer,[switch]$Capturas,[string]$Salida,
      [string]$Python,[string]$PolicyPython,[string]$DeployPath,[string]$LocoDeployPath)
$ErrorActionPreference='Stop'
$bundle=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $Salida) {
    $Salida = Join-Path $bundle ('validation/lateral_keeper_h2/'+$Ensayo+'_'+$Lado+'_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
}
$Salida = [IO.Path]::GetFullPath($Salida)
if ($Ensayo -eq 'maniobra') {
    . "$PSScriptRoot/_common.ps1"
    $python = Get-BundlePython -Python $Python
    if (-not $DeployPath) {
        $DeployPath = Join-Path $bundle 'app/RoboNaldo_Deploy'
        if (-not (Test-Path -LiteralPath (Join-Path $DeployPath 'g1_description/scene_with_ball.xml') -PathType Leaf)) {
            $DeployPath = Join-Path $bundle 'validation/keeper_live_20261030/package/app/RoboNaldo_Deploy'
        }
    }
    $deploy = (Resolve-Path -LiteralPath $DeployPath).Path
    $arguments = @('-X','utf8','-u','-B','-m','experiments.lateral_keeper_h2.dive_demo',
        '--deploy',$deploy,'--output',$Salida,'--side',$Lado)
} else {
    . "$PSScriptRoot/_experiment_paths.ps1"
    $paths = Resolve-ExperimentPaths -Bundle $bundle -Python $Python -PolicyPython $PolicyPython -DeployPath $DeployPath -LocoDeployPath $LocoDeployPath
    $python = $paths.Python
    $mode = @{'equilibrio'='balance'; 'transicion'='transfer'; 'maniobra_historica'='maneuver'}[$Ensayo]
    $arguments = @('-X','utf8','-u','-B','-m','experiments.lateral_keeper_h2.run',
        '--deploy',$paths.DeployPath,'--loco-deploy',$paths.LocoDeployPath,'--policy-python',$paths.PolicyPython,
        '--output',$Salida,'--mode',$mode,'--side',$Lado)
}
if ($Viewer) { $arguments+='--viewer' }
if ($Capturas) { $arguments+='--capture' }
Push-Location -LiteralPath (Join-Path $bundle 'app/RoboPenalty')
try { & $python @arguments; $code=$LASTEXITCODE } finally { Pop-Location }
exit $code
