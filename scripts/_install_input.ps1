# Installation input only. Never changes resources or grants permissions.
function Resolve-InstallInteraction {
    param([switch]$Interactivo, [switch]$NoInteractivo)
    if ($Interactivo -and $NoInteractivo) { throw 'Elegir -Interactivo o -NoInteractivo, no ambos.' }
    if ($NoInteractivo) { return $false }
    if ($Interactivo) { return $true }
    try { return [Environment]::UserInteractive -and -not [Console]::IsInputRedirected }
    catch { return $false }
}

function Get-InstallDeployFolder {
    param([string]$ExplicitPath, [bool]$Needed, [bool]$Ask)
    if ($ExplicitPath) { return $ExplicitPath }
    if (-not $Needed -or -not $Ask) { return '' }
    Write-Host ''
    Write-Host 'Faltan recursos Deploy adaptados. La copia oficial sola NO alcanza.'
    Write-Host 'Si ya obtuvo legitimamente una copia TP07 compatible, indique su carpeta.'
    Write-Host 'ENTER sin ruta: preparar solo lo disponible; el juego seguira bloqueado.'
    $answer = (Read-Host 'Carpeta Deploy (sin modificar la fuente)').Trim()
    if ($answer.Length -ge 2) {
        if (($answer.StartsWith('"') -and $answer.EndsWith('"')) -or
            ($answer.StartsWith("'") -and $answer.EndsWith("'"))) {
            $answer = $answer.Substring(1, $answer.Length - 2)
        }
    }
    return $answer
}

function Get-InstallResourceState {
    param([string]$Executable, [string]$App, [switch]$Full)
    $arguments = @('-X','utf8','-E','-s','-B','-m','portability.diagnose','--json')
    if (-not $Full) { $arguments += '--resources-only' }
    Push-Location -LiteralPath $App
    try {
        $lines = & $Executable @arguments
        $code = $LASTEXITCODE
        if ($code -ne 0 -and $code -ne 1) { throw 'El diagnostico no pudo ejecutarse.' }
        return (($lines -join "`n") | ConvertFrom-Json)
    } finally { Pop-Location }
}

function Test-OnlyExpectedDeployMissing {
    param($Details)
    $targets = @($Details.licensing.resources | ForEach-Object { $_.target })
    $problems = @($Details.external.problems)
    if ($targets.Count -ne 26 -or $problems.Count -ne 26) { return $false }
    if (@($problems | ForEach-Object { $_.resource } | Sort-Object -Unique).Count -ne 26) { return $false }
    foreach ($problem in $problems) {
        if ($problem.kind -ne 'missing' -or $targets -notcontains $problem.resource) { return $false }
    }
    return $true
}
