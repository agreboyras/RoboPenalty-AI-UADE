param(
    [string]$Python, [switch]$Headless, [int]$Seed = 2026, [switch]$SinPublicidad, [switch]$VisorLiviano = $true,
    [switch]$Voz, [ValidateSet('gpt-transcribe','whisper-1')][string]$ModeloTranscripcion = 'gpt-transcribe',
    [switch]$VisorCompleto
)
& "$PSScriptRoot/_jugar.ps1" -Mode directed -Python $Python -Headless:$Headless -Seed $Seed `
    -SinPublicidad:$SinPublicidad -VisorLiviano:$VisorLiviano -Voz:$Voz -ModeloTranscripcion $ModeloTranscripcion `
    -VisorCompleto:$VisorCompleto
exit $LASTEXITCODE
