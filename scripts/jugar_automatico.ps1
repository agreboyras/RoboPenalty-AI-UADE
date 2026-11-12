param([string]$Python, [switch]$Headless, [int]$Seed = 2026, [switch]$SinPublicidad,
      [switch]$VisorLiviano = $true, [switch]$VisorCompleto, [switch]$ArqueroLibre, [string]$PolicyPython, [string]$LocoDeployPath, [switch]$IzquierdaAbierta)
& "$PSScriptRoot/_jugar.ps1" -Mode auto -Python $Python -Headless:$Headless -Seed $Seed `
    -SinPublicidad:$SinPublicidad -VisorLiviano:$VisorLiviano -VisorCompleto:$VisorCompleto -ArqueroLibre:$ArqueroLibre `
    -PolicyPython $PolicyPython -LocoDeployPath $LocoDeployPath -IzquierdaAbierta:$IzquierdaAbierta
exit $LASTEXITCODE
