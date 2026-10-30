param([string]$Python, [switch]$Headless, [int]$Seed = 2026)
& "$PSScriptRoot/_jugar.ps1" -Mode auto -Python $Python -Headless:$Headless -Seed $Seed
exit $LASTEXITCODE
