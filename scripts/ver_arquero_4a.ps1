param([ValidateSet('sin-pelota','tiro')][string]$Ensayo = 'sin-pelota',
      [ValidateSet('LEFT','RIGHT')][string]$Lado = 'LEFT', [switch]$Experimental,
      [ValidateSet('keeper','behind','execution','overview','goal','follow')][string]$Camara,
      [string]$Accion = 'right_inter_m080', [string]$Python)
. "$PSScriptRoot/_common.ps1"
$exe = Get-BundlePython -Python $Python
& "$PSScriptRoot/verificar.ps1" -Python $exe
if ($LASTEXITCODE -ne 0) { throw 'Se requiere una instalacion completa de 104/104 recursos y paquetes. No se buscaran recursos en otros proyectos.' }
$app = Join-Path $PSScriptRoot '../app/RoboPenalty'
$caseName = if ($Ensayo -eq 'tiro') { 'nominal' } else { 'no-ball' }
$arguments = @('-X','utf8','-E','-s','-B','-m','experiments.keeper_saves.live_viewer',
               '--case',$caseName,'--side',$Lado,'--action',$Accion)
if ($Experimental) { $arguments += '--experimental' }
if ($Camara) { $arguments += @('--camera',$Camara) }
Push-Location -LiteralPath $app
try { & $exe @arguments; $code = $LASTEXITCODE } finally { Pop-Location }
exit $code
