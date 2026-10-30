param([string]$DeployPath, [string]$Python, [switch]$Inspeccionar)
. "$PSScriptRoot/_common.ps1"
$exe = Get-BundlePython -Python $Python
if (-not $DeployPath) { $DeployPath = Read-Host 'Carpeta Deploy adaptada obtenida legitimamente' }
$source = (Resolve-Path -LiteralPath $DeployPath -ErrorAction Stop).Path
$app = Join-Path $PSScriptRoot '../app/RoboPenalty'
$arguments = @('-X','utf8','-E','-s','-B','-m','portability.local_import',$source)
if ($Inspeccionar) { $arguments += '--inspect' }
Push-Location -LiteralPath $app
try {
    & $exe @arguments
    $code = $LASTEXITCODE
} finally { Pop-Location }
exit $code
