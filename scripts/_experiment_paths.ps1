# Path selection only. Physical drivers retain their SHA-256 and control checks.
function Resolve-ExperimentPaths {
    param([Parameter(Mandatory=$true)][string]$Bundle,
          [string]$Python,[string]$PolicyPython,[string]$DeployPath,[string]$LocoDeployPath)
    if (-not $Python) {
        $Python=Join-Path $Bundle '.venv/Scripts/python.exe'
        if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
            $Python=Join-Path $Bundle 'validation/etapa2_final_20261030/RoboPenalty AI UADE/.venv/Scripts/python.exe'
        }
    }
    if (-not $PolicyPython) {
        $PolicyPython=Join-Path $Bundle 'validation/envs/keeper/Scripts/python.exe'
        if (-not (Test-Path -LiteralPath $PolicyPython -PathType Leaf)) {
            $PolicyPython=Join-Path $Bundle 'validation/keeper_balance4b/.venv/Scripts/python.exe'
        }
    }
    if (-not $DeployPath) {
        $DeployPath=Join-Path $Bundle 'app/RoboNaldo_Deploy'
        if (-not (Test-Path -LiteralPath (Join-Path $DeployPath 'policy/robonaldo/FreeKick.py') -PathType Leaf)) {
            $DeployPath=Join-Path $Bundle 'validation/keeper_live_20261030/package/app/RoboNaldo_Deploy'
        }
    }
    if (-not $LocoDeployPath) {$LocoDeployPath=Join-Path $Bundle '../RoboNaldo_Deploy'}
    $result=@{}
    foreach ($entry in @(@('Python',$Python,'Leaf'),@('PolicyPython',$PolicyPython,'Leaf'),
                        @('DeployPath',$DeployPath,'Container'),@('LocoDeployPath',$LocoDeployPath,'Container'))) {
        $name=$entry[0];$path=$entry[1]
        if (-not (Test-Path -LiteralPath $path -PathType $entry[2])) {
            throw "Falta -$name. Indicar una ruta existente. Ver docs/ENTREGA_EXPERIMENTOS.md. No se descargan recursos."
        }
        $result[$name]=(Resolve-Path -LiteralPath $path).Path
    }
    foreach ($file in @('policy/loco_mode/model/policy_29dof.pt','policy/loco_mode/config/LocoMode.yaml','deploy_mujoco/config/mujoco.yaml')) {
        if (-not (Test-Path -LiteralPath (Join-Path $result.LocoDeployPath $file) -PathType Leaf)) {
            throw "-LocoDeployPath no contiene $file. El perfil de 104 recursos de la partida no incluye la politica de equilibrio. Ver docs/ENTREGA_EXPERIMENTOS.md."
        }
    }
    return [PSCustomObject]$result
}
