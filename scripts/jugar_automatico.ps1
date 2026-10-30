param([string]$Python, [switch]$Headless, [int]$Seed = 2026, [switch]$SinPublicidad)
& "$PSScriptRoot/_jugar.ps1" -Mode auto -Python $Python -Headless:$Headless -Seed $Seed -SinPublicidad:$SinPublicidad
exit $LASTEXITCODE
