# Entrega de experimentos de arquero — H1 a H4A

Guía para continuar el trabajo, sin sustituir la partida estable. Esta entrega **no es autónoma**: requiere recursos externos legítimamente obtenidos y compatibles. No publicar `validation/`, checkpoints ni entornos virtuales.

## 1. Qué se entrega y qué está demostrado

| Experimento | Implementación | Resultado demostrado y límite |
|---|---|---|
| H1 | `free_keeper_stadium_h1` | G1 libre en estadio, equilibrio y tiro físico original. Sin nueva maniobra |
| H2 | `lateral_keeper_h2` | Transferencia de control y movimiento lateral físico; lento, arquero apartado; no atajada |
| H2.5 | `keeper_center_h25` | Maniobra desde el centro, variantes temporales; sin intercepción demostrada |
| H3A | `central_block_h3a` | Central: referencia GOAL y 3/3 SAVE pasivos por contacto físico, ventana 14 s |
| H3B | `passive_coverage_h3b` | Cinco tiros: central SAVE; centro-izquierda contacto seguido de GOAL; tres derechos GOAL sin contacto |
| H3C | `low_block_h3c` | Residual ejecutado; empeoró el contacto; no atajada activa |
| H3D | `weight_transfer_h3d` | Transferencia/unloading reales, pero sin avance útil de la pierna dentro de 0,874 s; secuencia no viable |
| H4A | `shadow_agent_h4a` | Percepción, predicción y recomendación sin controlar motores; cinco trazas exactas frente a H3B |

Los resultados anteriores corresponden a condiciones nominales del equipo del autor. No son probabilidades de éxito ni robustez global. H4A no causa nuevas atajadas y no aprende automáticamente. 4C/goalkeeper.pt no participa en estos ocho experimentos.

## 2. Obtener el código

Una vez publicada esta entrega en la rama experimental, desde una carpeta de trabajo:

```powershell
git -c core.autocrlf=false clone --branch feature/atajadas-arquero --single-branch https://github.com/agreboyras/RoboPenalty-AI-UADE.git
Set-Location -LiteralPath .\RoboPenalty-AI-UADE
```

También puede descargarse el ZIP de **esa rama**. Estos comandos son instrucciones para el destinatario; no se ejecutaron en la auditoría. En la auditoría había 315 archivos versionados y los ocho módulos nuevos aún no estaban incorporados a Git. Verificar que el checkout recibido incluya sus carpetas y los nueve scripts enumerados en el informe de auditoría.

No cambiar a `main` para buscar estos experimentos. Los modos públicos de 8C/9A y el estadio 7D siguen siendo las referencias estables.

## 3. Dependencias externas y permisos

Son dos conjuntos diferentes:

1. **FreeKick + modelo Unitree:** perfil congelado de **104 recursos** en `app/RoboPenalty/portability/runtime_profile.json`. Se necesitan los 78 incluidos y los 26 de Deploy adaptado que importa el instalador. La guía de [instalación Windows](INSTALACION_WINDOWS.md) explica el origen TP07 fijado en `ce4b34d1bccfd0420a81bf1688271d86feb8a117`, sus adaptaciones y las restricciones. Deploy oficial solo no reemplaza ese conjunto. La importación produce bytes canónicos y conserva la verificación SHA-256; no publicar esos 26 archivos.
2. **Equilibrio libre:** una carpeta externa configurada con `-LocoDeployPath`, con tres archivos en su estructura original:

| Archivo relativo a LocoDeployPath | Integridad exigida por el adaptador |
|---|---|
| `policy/loco_mode/model/policy_29dof.pt` | SHA-256 bytes exactos `d1d91b0201beeb649a4624ba40052d10fe4aebe98bf6f4847decf75dd1fee2da` |
| `policy/loco_mode/config/LocoMode.yaml` | SHA-256 tras CRLF→LF `9be1972ff8f7b5cba57e428006d00a2b1c913b1d8253b5f1cb47294e286a8c0f` |
| `deploy_mujoco/config/mujoco.yaml` | SHA-256 tras CRLF→LF `90e51deaa22198e56fd638c117fe985f334c536a390bf0299ba1cadb0dbd3c7c` |

El checkpoint pesa 2.149.330 bytes. Se verificó que coincide exactamente con el blob de la copia Git local del commit TP07 anterior; ambos YAML coinciden canónicamente. No se verificó de nuevo su disponibilidad remota mediante descarga. No hace falta ejecutar `LocoMode.py`, el SDK de Unitree o el joystick: nuestro adaptador usa solo esos tres archivos y PyTorch.

**Tener 104/104 no incluye estos tres archivos adicionales.** El manifiesto histórico de 209 recursos sí registra locomoción, pero no es el perfil mínimo de la partida. No modificar sus hashes.

Los XML/meshes Unitree incluidos están cubiertos por sus avisos BSD-3-Clause. No extender esa licencia a los checkpoints, ONNX, NPZ, escenas o código Deploy. Los permisos de Deploy y de la política de locomoción siguen pendientes de aclaración; que estén en un repositorio público no concede derechos. Cada integrante debe contar con acceso legítimo y condiciones de uso aplicables. Si no los tiene, detener la ejecución física y consultar al equipo/titulares; no sustituir archivos ni pedir copias públicas de los pesos. Véase [THIRD_PARTY.md](../THIRD_PARTY.md).

## 4. Preparar los entornos

Windows, CPython **3.12 x64**, PowerShell 5.1+ y controlador gráfico compatible para el visor. No se requiere CUDA. Separar el Python principal del proceso auxiliar de inferencia CPU.

Desde la raíz del proyecto:

```powershell
py -3.12 -c "import sys; print(sys.version); assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32"

# Solo si Windows bloquea los scripts locales que ya revisaste:
Set-ExecutionPolicy -Scope Process RemoteSigned

# Seleccionar una copia compatible poseída legítimamente; no se copia al historial Git.
$deployOrigen = Read-Host 'Ruta de la raiz Deploy adaptada TP07 compatible'
.\scripts\instalar.ps1 -NoInteractivo -DeployPath $deployOrigen
if ($LASTEXITCODE -ne 0) { throw 'Instalacion incompleta: revisar el diagnostico antes de continuar' }
.\scripts\verificar.ps1 -Python .\.venv\Scripts\python.exe
if ($LASTEXITCODE -ne 0) { throw 'Falta integridad, paquetes o recursos' }

# Entorno NUEVO para inferencia; no reutilizar ni cambiar el de otro proyecto.
# Estos comandos descargan paquetes Python si el destinatario decide ejecutarlos;
# esta auditoria NO los ejecuto y NO descarga checkpoints.
py -3.12 -m venv .\validation\envs\keeper
& .\validation\envs\keeper\Scripts\python.exe -m pip install torch==2.9.0 --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw 'Fallo instalando PyTorch CPU' }
& .\validation\envs\keeper\Scripts\python.exe -m pip install numpy==2.5.3 PyYAML==6.0.3
if ($LASTEXITCODE -ne 0) { throw 'Fallo instalando dependencias auxiliares' }
& .\validation\envs\keeper\Scripts\python.exe -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependencias auxiliares incompatibles' }
```

La aplicación usa el lock existente `app/RoboPenalty/requirements-windows.txt`, con MuJoCo 3.13.0, NumPy 2.5.3 y ONNX Runtime 1.30.0, entre otros. El worker solo necesita Torch, NumPy y PyYAML; no crea una simulación ni necesita MuJoCo. El entorno privado del autor contiene además MuJoCo por ensayos anteriores, pero no es importado por ese worker.

Versiones observadas: Python principal 3.12.14; auxiliar 3.12.10; Torch 2.9.0+cpu. Los paquetes y versiones se verificaron en los entornos existentes, no instalando otra vez desde Internet. Si una versión fijada no está disponible, informar el bloqueo: no sustituirla silenciosamente ni prometer igualdad bit a bit entre equipos distintos.

## 5. Configurar rutas una sola vez

```powershell
$locoOrigen = Read-Host 'Ruta de la raiz externa que contiene policy/loco_mode/model/policy_29dof.pt'
$comun = @{
    Python         = (Resolve-Path .\.venv\Scripts\python.exe).Path
    PolicyPython   = (Resolve-Path .\validation\envs\keeper\Scripts\python.exe).Path
    DeployPath     = (Resolve-Path .\app\RoboNaldo_Deploy).Path
    LocoDeployPath = (Resolve-Path -LiteralPath $locoOrigen).Path
}
```

Todos los lanzadores H1–H4A aceptan esos cuatro parámetros; son ejecutables/carpetas, no URLs. Se admiten rutas con espacios. No necesitan que la copia externa se llame RoboNaldo_Deploy ni esté junto al repositorio. El modelo Unitree sigue estando en `app/unitree_mujoco`, con la estructura interna publicada.

Sin parámetros se conservan respaldos locales antiguos para el autor; **no son instrucciones para un compañero**. En un clon limpio usar `@comun`. Las verificaciones de hashes, contrato de observaciones, límites efectivos y recurrente siguen en Python, sin cambios; el helper PowerShell solo selecciona rutas y comprueba su existencia.

## 6. Primera ejecución: H1 y H3A

```powershell
# Un tiro lateral con el arquero apartado: verifica estadio, FreeKick y equilibrio.
.\scripts\probar_estadio_libre_h1.ps1 @comun -Ubicacion apartado -Accion right_inter_m080 -Viewer -Camara behind

# Referencia nueva para demostrar el bloqueo central; salidas siempre nuevas.
$sesion = Join-Path (Get-Location).Path ('validation/entrega_'+(Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
.\scripts\probar_bloqueo_central_h3a.ps1 @comun -Ubicacion apartado -Salida "$sesion/h3a_referencia"
if ($LASTEXITCODE -ne 0) { throw 'Referencia H3A no valida' }
.\scripts\probar_bloqueo_central_h3a.ps1 @comun -Ubicacion centro -Referencia "$sesion/h3a_referencia/interception.json" -Salida "$sesion/h3a_centro" -Viewer -Camara goal
```

H1/H3A duran 14 s simulados. El tiempo real depende del equipo. No arrastrar al robot con el mouse: las fuerzas externas invalidan la prueba. Cerrar la ventana o Ctrl+C interrumpe; un ensayo incompleto no es evidencia de éxito. Para repetir usar otra `$sesion` o dejar que el lanzador genere una salida fechada.

El central de H3A se evalúa con `interception.json`. El reporte heredado H1 puede marcar `feet_only=false` y su antiguo límite de 10 mm por contacto legítimo con pelota: eso ya existe en las referencias, no es un cambio del lanzador. H3A conserva su protocolo de contacto de 20 mm. No relajar esos criterios ni usar el reporte de equilibrio solo para declarar SAVE.

## 7. Regenerar referencias H3B y ejecutar H4A

No hace falta recibir resultados del autor. H3B genera primero las referencias apartadas y los baselines centrados **en la computadora del destinatario**, con iguales recursos y entorno:

```powershell
$acciones = @('center','left_near_b060','right_inter_m080','right_open_m100','right_corner_m140')
foreach ($accion in $acciones) {
    .\scripts\probar_cobertura_pasiva_h3b.ps1 @comun -Accion $accion -Ubicacion apartado -Salida "$sesion/ref_$accion"
    if ($LASTEXITCODE -ne 0) { throw "Referencia invalida: $accion" }
    .\scripts\probar_cobertura_pasiva_h3b.ps1 @comun -Accion $accion -Ubicacion centro -Referencia "$sesion/ref_$accion/interception.json" -Salida "$sesion/base_$accion"
    if ($LASTEXITCODE -ne 0) { throw "Baseline invalido: $accion" }
}

# Visor del agente shadow: lee las referencias recien creadas.
.\scripts\probar_agente_shadow_h4a.ps1 @comun -Accion center -Referencia "$sesion/ref_center/interception.json" -Baseline "$sesion/base_center" -Salida "$sesion/shadow_center" -Viewer -Camara behind
if ($LASTEXITCODE -ne 0) { throw 'Revisar validez, interrupcion o divergencia shadow central' }

# Los otros cuatro: omitir -Viewer para ejecucion headless.
foreach ($accion in $acciones | Where-Object { $_ -ne 'center' }) {
    .\scripts\probar_agente_shadow_h4a.ps1 @comun -Accion $accion -Referencia "$sesion/ref_$accion/interception.json" -Baseline "$sesion/base_$accion" -Salida "$sesion/shadow_$accion"
    if ($LASTEXITCODE -ne 0) { throw "Revisar validez o divergencia shadow: $accion" }
}
```

H4A compara bit a bit con el baseline H3B elegido. No esconder diferencias mediante tolerancias. En otra CPU/versión puede cambiar una reproducción histórica; separar eso de la comparación shadow/sin agente bajo el mismo entorno. Estos comandos se comprobaron en cuanto a parámetros y rutas; **no se ejecutó ahora una instalación limpia ni se regeneraron penalidades**, para no descargar dependencias o producir trazas grandes.

Mínimo de entrada por tiro a H4A:

- Referencia apartada: únicamente `interception.json`.
- Baseline centrado: `interception.json`, `trace.npz`, `interception_trace.npz`, `ball_keeper_contacts.json`.

El conjunto existente de esos cinco pares ocupa **59.484.336 bytes (59,48 MB)**. No incluye entornos, modelos o imágenes. Es regenerable y no se recomienda subirlo a Git. Para auditoría histórica completa conservar localmente todos los resultados originales, que contienen más evidencia; el mínimo anterior sirve para ejecutar el comparador, no sustituye el archivo científico completo.

## 8. Observar los otros experimentos

Con `$comun` y las referencias anteriores:

```powershell
# H2: original, apartado; H2.5: centrado. No son atajadas demostradas.
.\scripts\probar_maniobra_h2.ps1 @comun -Ensayo maniobra_historica -Lado LEFT -Viewer
.\scripts\probar_maniobra_h2.ps1 @comun -Ensayo maniobra_historica -Lado RIGHT -Viewer
.\scripts\probar_centro_h25.ps1 @comun -Variante original -Lado LEFT -Viewer
.\scripts\probar_centro_h25.ps1 @comun -Variante original -Lado RIGHT -Viewer

# H3C conserva su protocolo negativo; no recalibrar para esta entrega.
.\scripts\probar_bloqueo_bajo_h3c.ps1 @comun -Accion left_near_b060 -Modo passive -Referencia "$sesion/ref_left_near_b060/interception.json" -Viewer
.\scripts\probar_bloqueo_bajo_h3c.ps1 @comun -Accion left_near_b060 -Modo active -Amplitud 0.04 -Referencia "$sesion/ref_left_near_b060/interception.json" -Viewer

# H3D usa G1 + suelo, sin estadio/penal; no hay una nueva maniobra de bloqueo.
.\scripts\probar_transferencia_h3d.ps1 @comun -Modo baseline -Viewer
.\scripts\probar_transferencia_h3d.ps1 @comun -Modo transfer -Viewer
```

La comprobación de 104 recursos sigue siendo necesaria incluso en H3D porque compila una referencia H1 para verificar equivalencia física del G1/suelo. No confundir un código de ensayo negativo con que esté autorizada una nueva calibración.

## 9. Comprobaciones y limitaciones de herramientas históricas

```powershell
& .\.venv\Scripts\python.exe -X utf8 -B tests/run_tests.py --include-core

Push-Location .\app\RoboPenalty
try {
    & $comun.Python -X utf8 -B -m unittest experiments.shadow_agent_h4a.test_agent experiments.passive_coverage_h3b.test_coverage experiments.central_block_h3a.test_block experiments.free_keeper_stadium_h1.test_hito1 experiments.lateral_keeper_h2.test_maneuver experiments.keeper_center_h25.test_center experiments.low_block_h3c.test_maneuver experiments.weight_transfer_h3d.test_support -v
} finally { Pop-Location }
```

El test histórico de composición H1 busca el Deploy de `validation/keeper_live_20261030/package/app/RoboNaldo_Deploy` y omite esa clase si no existe. **Tests aprobados con omisiones no demuestran composición ni física.** No se cambió ese test: las ejecuciones físicas deben validar la composición y registrar checks. Los demás tests de reglas no prueban una atajada nueva.

Los analizadores históricos H3A/H3B/H3C/H3D leen además snapshots SHA y nombres de ensayos del autor. El renderizador offline H3D tiene una ruta local rígida al Deploy. Son herramientas de reproducción del archivo histórico, no lanzadores portátiles. No se adaptaron para ampliar el alcance. Para un destinatario, usar los lanzadores configurables y los JSON de cada ensayo; H4A `analyze.py` sí admite carpetas explícitas. Tras cambiar lanzadores, los snapshots viejos pueden informar esos scripts como diferentes: no reemplazar ni reescribir hashes históricos.

## 10. Qué conservar y qué no publicar

- Conservar todos los componentes propios transitivos ya publicados, las ocho carpetas nuevas completas (código, tests y documentación), sus ocho lanzadores y `_experiment_paths.ps1`.
- Conservar el catálogo 8C y sus 37 JSON exactos, manifiestos, requisitos, licencias Unitree y avisos. No reconstruir una entrega seleccionando solo las ocho carpetas: importan fases anteriores y `free_keeper4b`.
- Mantener excluidos `validation/`, entornos, grabaciones, capturas temporales, checkpoints `.pt`, ONNX, NPZ y los 26 recursos importados. Los XML/STL BSD revisados sí se conservan.
- **Atención:** el `.gitignore` actual excluye `validation/`, ONNX y NPZ, pero no tiene una regla global `*.pt`. No copiar pesos fuera de su carpeta externa y no usar una incorporación indiscriminada. Esta tarea no cambió las exclusiones; revisar la lista exacta antes del commit manual.

El inventario informativo [RECURSOS_EXPERIMENTOS.json](RECURSOS_EXPERIMENTOS.json) enumera los 104 archivos del perfil y los tres adicionales de locomoción, con tamaños, procedencia y estado de permisos. No sustituye ni modifica los manifiestos de ejecución.

La instalación totalmente autónoma sigue bloqueada por disponibilidad legítima/permisos de los recursos externos, no por falta de código para copiar `validation/`. Recomendación: entregar código y esta guía, compartir resultados resumidos propios, y regenerar las referencias en cada equipo. No anunciar reproducibilidad completa en otra computadora hasta probar allí los recursos, entorno y ensayos físicos.
