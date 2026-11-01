# Auditoría de entrega experimental — 2026-11-01

**Veredicto: entregable como código experimental documentado, con dependencias externas y restricciones explícitas. No es una distribución autónoma ni se ha validado de nuevo una instalación limpia en esta tarea.**

Rama consultada: `feature/atajadas-arquero`. Hay 315 archivos versionados; ninguno de los ocho módulos nuevos está aún en ese conjunto. No se ejecutaron operaciones Git de escritura ni se cambió de rama. No se recomienda integrar experimentos en `main`.

## Dependencias reales

| Módulo | Dependencias propias principales | Entradas históricas adicionales para ejecutar |
|---|---|---|
| H1 | `phase2` FreeKick/RobotIndex, `phase4a.scenarios`, `free_keeper4b.policy`, cliente/worker propios, presentación 7D | Ninguna salida antigua; entornos y recursos configurables |
| H2 | H1, `lateral_keeper_h2.maneuver`, presentación H2/7D | Ninguna salida antigua |
| H2.5 | H1 + conductor H2 cargado de forma aislada, trayectoria/presentación propias | Ninguna salida antigua |
| H3A | Conductor H1 aislado, Recorder H3A, clasificador `phase4a.evaluation` | JSON de referencia apartada para demostrar SAVE; regenerable |
| H3B | H1 + Recorder H3A, catálogo 8C y clasificación de cobertura | JSON de referencia apartada de la misma acción/calibración para demostrar SAVE; regenerable |
| H3C | H1, Recorder H3A, residual propio y política de equilibrio | Referencia apartada de la acción; ahora ruta seleccionable |
| H3D | H1 para comparar composición, H3A para registro, `H3C.policy_target`, política 4B.1; renderer opcional usa helper PNG de 4B.1 | Ninguna salida antigua para `run`; análisis histórico sí requiere snapshots |
| H4A | H1 + H3A/H3B, predictor sin modificar `phase3b.predictor`, agente propio | Referencia apartada + baseline H3B de idéntica acción, rutas seleccionables |

La presentación 7D importa piezas visuales de 7C, 7B y 6A. Se requieren las fases previas publicadas y los 37 JSON del catálogo 8C, no solamente las ocho carpetas. El proceso de política usa `experiments/free_keeper4b/policy.py`, pero no necesita otro simulador ni la política 4C.

### Qué es imprescindible de validation/

La ubicación dentro de `validation/` de los recursos/entornos **no es imprescindible**: ahora los lanzadores aceptan `-Python`, `-PolicyPython`, `-DeployPath` y `-LocoDeployPath`. El directorio `validation/` se mantiene como destino obligatorio de nuevas salidas, preservando las restricciones de los conductores.

- H1: Python físico con dependencias; Python Torch CPU; FreeKick/Unitree exactos y política/configs de equilibrio. Ningún resultado previo.
- H3A/H3B: lo anterior; para una clasificación con contrafactual de gol, `interception.json` de referencia apartada. Se genera primero en el mismo equipo.
- H4A por tiro: referencia apartada `interception.json`; baseline centrado con `interception.json`, `trace.npz`, `interception_trace.npz`, `ball_keeper_contacts.json`. Cinco tiros: 25 archivos, **59.484.336 bytes**, frente a los 7,79 GB de `validation/` informados por el usuario. Se midió el mínimo, no se volvió a recorrer ni se recomienda copiar el archivo completo de 7,79 GB.

`report.json`, `contacts.json`, imágenes y otros ficheros conservan evidencia adicional del experimento, pero no son entradas mínimas del conductor H4A actual. No borrar resultados originales ni confundir este recorte operativo con un archivo científico completo. Preferir regeneración a publicar trazas antiguas.

Los analizadores históricos H3A/H3B/H3C/H3D exigen además archivos SHA/nombres de ensayos concretos; el renderer H3D conserva una ruta local. El test de composición H1 usa un Deploy privado fijo y se omite si falta. No se adaptaron esas herramientas: la portabilidad mejorada abarca los lanzadores de ejecución. No usar tests omitidos como prueba física.

## Recursos y permisos

Detalle por archivo: [RECURSOS_EXPERIMENTOS.json](RECURSOS_EXPERIMENTOS.json), 107 filas informativas. Los manifiestos operativos permanecen intactos.

| Conjunto | Cantidad | Tamaño observado | Ubicación de ejecución | Procedencia / permisos |
|---|---:|---:|---|---|
| Unitree MuJoCo: XML G1, 36 meshes y LICENSE | 38 | 18.576.453 bytes | `app/unitree_mujoco` | `unitreerobotics/unitree_mujoco` @ `1eb6642e3f3fdfb7fb13a9794fd6a2dd93ea0e7d`; BSD-3-Clause |
| Meshes Unitree ROS | 35 | 19.666.440 bytes | `DeployPath/g1_description/meshes` | `unitreerobotics/unitree_ros` @ `38a9b00ecbff0b70e85a7627eb9c65db9a2341f7`; BSD-3-Clause |
| Estructura vacía propia | 5 | 0 bytes | `DeployPath` | `__init__.py` generados, no aportan licencia a otros archivos |
| Deploy adaptado pendiente, incluidos los dos binarios siguientes | 26 | 3.119.811 bytes | `DeployPath` importado localmente | Origen/adaptaciones en `external_sources.json`; permisos pendientes, no publicar |
| ONNX FreeKick (subconjunto de los 26) | 1 | 1.795.420 bytes | `policy/robonaldo/model/policy-obs-aic.onnx` | Derechos de pesos no verificados; no presentarlo como entrenado por el equipo |
| NPZ FreeKick (subconjunto de los 26) | 1 | 1.098.498 bytes | `policy/robonaldo/model/freekick_motion.npz` | Condiciones de datos/movimiento pendientes; bytes exactos requeridos |
| Checkpoint de equilibrio, adicional al perfil 104 | 1 | 2.149.330 bytes | `LocoDeployPath/policy/loco_mode/model/policy_29dof.pt` | Coincide byte a byte con blob TP07 fijado; autoría/licencia de pesos no demostradas |
| Configuración LocoMode, adicional | 1 | 1.812 bytes en copia CRLF | `LocoDeployPath/policy/loco_mode/config/LocoMode.yaml` | Coincide con blob TP07 tras CRLF→LF; permiso de redistribución no aclarado |
| Configuración PD, adicional | 1 | 824 bytes en copia CRLF | `LocoDeployPath/deploy_mujoco/config/mujoco.yaml` | Coincide con blob TP07 tras CRLF→LF; permiso de redistribución no aclarado |

No sumar ONNX/NPZ dos veces: forman parte de los 26. Total de 104 archivos del perfil: **41.362.704 bytes**; con los tres de equilibrio, **43.514.670 bytes**, sin paquetes Python, avisos auxiliares o resultados. Los YAML pueden tener menor tamaño con LF; se conserva la comprobación canónica ya existente. Los binarios no se normalizan.

Evidencia local de licencias: `app/unitree_mujoco/LICENSE` (Copyright 2016–2024 Unitree), `app/RoboNaldo_Deploy/LICENSE-Unitree-ROS.txt` (Copyright 2016–2022 Unitree) y [THIRD_PARTY.md](../THIRD_PARTY.md). BSD exige conservar copyright, condiciones y exención; en binarios reproducir los avisos en documentación/materiales; no usar al titular como respaldo comercial. No se aplica a pesos ni a código Deploy.

Para los 26, el manifiesto distingue 13 originales, ocho modificados TP07, tres añadidos TP07, un ONNX y un NPZ. Se conservan las atribuciones y el estado pendiente; modificaciones o disponibilidad pública no resuelven los derechos heredados. El código principal RoboNaldo con MIT no prueba permiso sobre todo Deploy. No se reabre ni sustituye la auditoría legal anterior.

La copia Git local de Deploy está en el commit TP07 `ce4b34d1bccfd0420a81bf1688271d86feb8a117`; el remoto origin observado se llama `agreboyrasFacu1/TP07-IA-G1-Futbol`, mientras que las referencias históricas del proyecto usan `agreboyras/TP07-IA-G1-Futbol`. La comprobación de los tres blobs fue local y por commit/hash: no se presupone que ambas URLs estén actualmente disponibles o sean intercambiables. No se descargó ni verificó de nuevo el servidor remoto.

Quien solo tenga el repositorio público puede leer código, documentación y ejecutar tests que no requieran recursos privados. **No puede ejecutar estos G1 libres solo por tener 78/104, ni siquiera por completar 104/104 si no tiene también los tres archivos de equilibrio compatibles.**

## Cambios mínimos de esta tarea

- Nueve scripts: ocho lanzadores ajustados y nuevo `_experiment_paths.ps1`.
- Todos admiten los cuatro parámetros externos; se mantienen los flags de ensayo/cámara/control y las verificaciones Python.
- H3C añade referencia explícita. H4A añade referencia y baseline explícitos; no queda obligado a usar nombres de ensayos del autor.
- Tres documentos nuevos: guía, informe de recursos y esta auditoría.
- Cero cambios en simulación, controles, predicción, agentes, pruebas históricas, resultados, calibraciones, políticas, XML, licencias, manifiestos operativos, `.gitignore` o inventario previo.

El helper prioriza `.venv` y el nuevo entorno sugerido `validation/envs/keeper`, con respaldo a las rutas privadas existentes. Eso conserva la comodidad local sin exigirla a los destinatarios. Indicar parámetros explícitos para una entrega reproducible.

## Comprobaciones realizadas

- 104/104 recursos físicos verificados contra sus SHA-256 existentes.
- Tres archivos de equilibrio presentes y compatibles; checkpoint exacto; YAML canónicos iguales a constantes del adaptador y a blobs locales TP07.
- Inferencia real auxiliar: 96 observaciones → 29 referencias finitas, comando físico cero, recurrente reiniciado a cero y normalizador sin cambios. Sin pasos físicos.
- `pip check`: correcto en ambos entornos privados existentes. No se instaló ni descargó nada.
- **176 tests distribución/core y 71 tests experimentales aprobados.**
- Los ocho puntos de entrada Python importaron correctamente y respondieron a `--help` en el entorno principal; no se avanzó física.
- Pruebas de lanzadores: cuatro casos agregados, con subcasos para los ocho scripts, en Windows PowerShell 5.1 y PowerShell 7. Incluyen parseo, rutas con espacios, paso de parámetros a CLI, conservación de respaldos locales y error ante ruta explícita inexistente. Se usó un intérprete simulado en fixtures aislados; **no equivale a una simulación física ni una instalación limpia**.
- Confirmación SHA-256 de que, de los 241 archivos preexistentes protegidos del alcance, solo cambiaron los ocho lanzadores autorizados. Código Python y resultados originales no cambiaron; estos últimos no se volvieron a ejecutar ni sobrescribir.
- No hay `.pt`, ONNX o NPZ en los 315 archivos versionados; no hay `validation/` versionada. `validation/`, ONNX y NPZ están excluidos. `.pt` **no** está excluido globalmente: no copiar pesos al árbol publicable y seleccionar explícitamente los archivos al preparar el commit manual. No se modificaron exclusiones porque el alcance de cambios se limitó a scripts/documentación.

Las primeras pruebas de PowerShell 5.1 encontraron su política de ejecución local y una peculiaridad del código de salida al manejar una excepción esperada. Se ajustó únicamente el arnés privado de comprobación (política por proceso hijo y salida explícita); las pruebas finales pasaron en ambos shells. No se cambiaron políticas globales ni parámetros físicos.

No se ejecutó otra tanda, se abrió un nuevo visor ni se produjo una traza grande en esta tarea. La evidencia física/visual sigue siendo la histórica documentada en cada módulo. Para afirmar reproducibilidad entre computadoras, el equipo debe instalar legítimamente los recursos y ejecutar las comparaciones allí.

## Recomendación de entrega y pendientes

Conservar los 315 archivos existentes; añadir las ocho carpetas propias y sus lanzadores/helper/documentación de la lista siguiente. No añadir los recursos externos pendientes ni `validation/`. Este informe no certifica de nuevo todos los permisos de los 315 archivos anteriores; conserva la auditoría/atribuciones previas y no añade código externo de 4C.

Pendientes: acceso legítimo/permisos de pesos y Deploy; disponibilidad del repositorio fuente en otro equipo; instalación real de las versiones fijadas; prueba física local del destinatario; herramientas de análisis/render histórico aún atadas al archivo del autor; revisión final del conjunto que se vaya a preparar manualmente en Git. No anunciar nuevas atajadas ni integrar el agente shadow con motores.

### Lista exacta de archivos adicionales recomendados

La lista se incorpora abajo, sin recursos externos ni salidas de ejecución: **73 archivos adicionales**, aproximadamente 0,46 MB. Incluye 61 archivos de los ocho módulos, nueve scripts y tres documentos. No sustituye los 315 archivos ya versionados.

```text
app/RoboPenalty/experiments/central_block_h3a/README.md
app/RoboPenalty/experiments/central_block_h3a/RESULTADOS.md
app/RoboPenalty/experiments/central_block_h3a/__init__.py
app/RoboPenalty/experiments/central_block_h3a/analyze.py
app/RoboPenalty/experiments/central_block_h3a/run.py
app/RoboPenalty/experiments/central_block_h3a/test_block.py
app/RoboPenalty/experiments/free_keeper_stadium_h1/README.md
app/RoboPenalty/experiments/free_keeper_stadium_h1/RESULTADOS.md
app/RoboPenalty/experiments/free_keeper_stadium_h1/__init__.py
app/RoboPenalty/experiments/free_keeper_stadium_h1/bootstrap.py
app/RoboPenalty/experiments/free_keeper_stadium_h1/policy_client.py
app/RoboPenalty/experiments/free_keeper_stadium_h1/policy_worker.py
app/RoboPenalty/experiments/free_keeper_stadium_h1/presentation.py
app/RoboPenalty/experiments/free_keeper_stadium_h1/run.py
app/RoboPenalty/experiments/free_keeper_stadium_h1/scene.py
app/RoboPenalty/experiments/free_keeper_stadium_h1/test_hito1.py
app/RoboPenalty/experiments/keeper_center_h25/README.md
app/RoboPenalty/experiments/keeper_center_h25/RESULTADOS.md
app/RoboPenalty/experiments/keeper_center_h25/__init__.py
app/RoboPenalty/experiments/keeper_center_h25/analyze.py
app/RoboPenalty/experiments/keeper_center_h25/presentation.py
app/RoboPenalty/experiments/keeper_center_h25/run.py
app/RoboPenalty/experiments/keeper_center_h25/test_center.py
app/RoboPenalty/experiments/keeper_center_h25/trajectory.py
app/RoboPenalty/experiments/lateral_keeper_h2/README.md
app/RoboPenalty/experiments/lateral_keeper_h2/RESULTADOS.md
app/RoboPenalty/experiments/lateral_keeper_h2/__init__.py
app/RoboPenalty/experiments/lateral_keeper_h2/maneuver.py
app/RoboPenalty/experiments/lateral_keeper_h2/presentation.py
app/RoboPenalty/experiments/lateral_keeper_h2/run.py
app/RoboPenalty/experiments/lateral_keeper_h2/test_maneuver.py
app/RoboPenalty/experiments/low_block_h3c/README.md
app/RoboPenalty/experiments/low_block_h3c/RESULTADOS.md
app/RoboPenalty/experiments/low_block_h3c/__init__.py
app/RoboPenalty/experiments/low_block_h3c/analyze.py
app/RoboPenalty/experiments/low_block_h3c/maneuver.py
app/RoboPenalty/experiments/low_block_h3c/run.py
app/RoboPenalty/experiments/low_block_h3c/test_maneuver.py
app/RoboPenalty/experiments/passive_coverage_h3b/README.md
app/RoboPenalty/experiments/passive_coverage_h3b/RESULTADOS.md
app/RoboPenalty/experiments/passive_coverage_h3b/__init__.py
app/RoboPenalty/experiments/passive_coverage_h3b/analyze.py
app/RoboPenalty/experiments/passive_coverage_h3b/run.py
app/RoboPenalty/experiments/passive_coverage_h3b/test_coverage.py
app/RoboPenalty/experiments/shadow_agent_h4a/README.md
app/RoboPenalty/experiments/shadow_agent_h4a/RESULTADOS.md
app/RoboPenalty/experiments/shadow_agent_h4a/__init__.py
app/RoboPenalty/experiments/shadow_agent_h4a/agent.py
app/RoboPenalty/experiments/shadow_agent_h4a/analyze.py
app/RoboPenalty/experiments/shadow_agent_h4a/run.py
app/RoboPenalty/experiments/shadow_agent_h4a/test_agent.py
app/RoboPenalty/experiments/weight_transfer_h3d/README.md
app/RoboPenalty/experiments/weight_transfer_h3d/RESULTADOS.md
app/RoboPenalty/experiments/weight_transfer_h3d/__init__.py
app/RoboPenalty/experiments/weight_transfer_h3d/analyze.py
app/RoboPenalty/experiments/weight_transfer_h3d/maneuver.py
app/RoboPenalty/experiments/weight_transfer_h3d/render.py
app/RoboPenalty/experiments/weight_transfer_h3d/run.py
app/RoboPenalty/experiments/weight_transfer_h3d/scene.py
app/RoboPenalty/experiments/weight_transfer_h3d/support.py
app/RoboPenalty/experiments/weight_transfer_h3d/test_support.py
docs/AUDITORIA_ENTREGA_EXPERIMENTAL.md
docs/ENTREGA_EXPERIMENTOS.md
docs/RECURSOS_EXPERIMENTOS.json
scripts/_experiment_paths.ps1
scripts/probar_agente_shadow_h4a.ps1
scripts/probar_bloqueo_bajo_h3c.ps1
scripts/probar_bloqueo_central_h3a.ps1
scripts/probar_centro_h25.ps1
scripts/probar_cobertura_pasiva_h3b.ps1
scripts/probar_estadio_libre_h1.ps1
scripts/probar_maniobra_h2.ps1
scripts/probar_transferencia_h3d.ps1
```
