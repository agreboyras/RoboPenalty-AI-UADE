param([ValidateSet('auto','directed')][string]$Mode, [string]$Python, [switch]$Headless, [int]$Seed = 2026,
      [switch]$SinPublicidad, [switch]$VisorLiviano = $true, [switch]$Voz,
      [ValidateSet('gpt-transcribe','whisper-1')][string]$ModeloTranscripcion = 'gpt-transcribe',
      [switch]$VisorCompleto)
. "$PSScriptRoot/_common.ps1"
$exe = Get-BundlePython -Python $Python
& "$PSScriptRoot/verificar.ps1" -Python $exe
if ($LASTEXITCODE -ne 0) {
    throw 'Partida BLOQUEADA: faltan recursos, paquetes o permisos. No se inicializo MuJoCo ni se busco Deploy fuera de este paquete.'
}
$app = Join-Path $PSScriptRoot '../app/RoboPenalty'
$stamp = (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [guid]::NewGuid().ToString('N').Substring(0,6)
$arguments = @('-X', 'utf8', '-E', '-s', '-B', '.\run_robopenalty.py', '--mode', $Mode,
    '--once', '--penalties', '5', '--seed', [string]$Seed, '--output', ".\phase9a\results\${Mode}_$stamp")
if (-not $Headless) {
    $arguments += '--viewer'
    if ($VisorCompleto -or -not $VisorLiviano) { $arguments += '--no-light-viewer' }
}
if ($SinPublicidad) { $arguments += '--no-institutional-ads' }
if ($Voz) { $arguments += @('--voice', '--transcription-model', $ModeloTranscripcion) }
if ($Mode -eq 'auto') { $arguments += '--autostart' }
Push-Location -LiteralPath $app
try {
    & $exe @arguments
    $code = $LASTEXITCODE
} finally { Pop-Location }
exit $code
