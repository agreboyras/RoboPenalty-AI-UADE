param([string]$Python, [switch]$ResourcesOnly, [switch]$Json)
. "$PSScriptRoot/_common.ps1"
$exe = Get-BundlePython -Python $Python
$app = Join-Path $PSScriptRoot '../app/RoboPenalty'
$arguments = @('-X', 'utf8', '-E', '-s', '-B', '-m', 'portability.diagnose')
if ($ResourcesOnly) { $arguments += '--resources-only' }
if ($Json) { $arguments += '--json' }
Push-Location -LiteralPath $app
try {
    & $exe @arguments
    $code = $LASTEXITCODE
} finally { Pop-Location }
exit $code
