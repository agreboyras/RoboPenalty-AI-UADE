param([string]$Python, [switch]$Headless, [int]$Seed = 2026, [switch]$SinPublicidad,
      [switch]$VisorLiviano = $true, [switch]$VisorCompleto)
& "$PSScriptRoot/_jugar.ps1" -Mode auto -Python $Python -Headless:$Headless -Seed $Seed `
    -SinPublicidad:$SinPublicidad -VisorLiviano:$VisorLiviano -VisorCompleto:$VisorCompleto
exit $LASTEXITCODE
