# Etapa 4C: goalkeeper.pt en su referencia MuJoCo-Warp

Evaluación experimental privada en Windows/CPU. **No integra la política en
RoboPenalty ni demuestra compatibilidad con su G1.** El entorno de referencia es
el port local G1-mjlab-soccer, no el Isaac Gym usado para entrenar originalmente.

## Observar y repetir

Desde PowerShell, en la raíz de RoboPenalty-AI-Complete:

```powershell
.\scripts\evaluar_arquero_4c.ps1 -Modo Verificar
.\scripts\evaluar_arquero_4c.ps1 -Modo Headless -Ensayos 5 -Semilla 2810
.\scripts\evaluar_arquero_4c.ps1 -Modo Visor -Ensayos 5 -Semilla 2810
```

El script encuentra la referencia en `../G1-mjlab-soccer`; para otra ubicación
use `-Referencia "ruta del checkout G1-mjlab-soccer"`. El checkpoint permanece
allí y debe tener el SHA-256 verificado por audit_checkpoint.py. No se copia.
Cada ejecución crea resultados nuevos en `validation/keeper_reference4c/`.
No sobrescribe los ensayos anteriores.

El visor original NativeMujocoViewer muestra un G1 libre y la pelota naranja.
Los tiros se generan con las condiciones parabólicas del proyecto de referencia;
no provienen de FreeKick. Permite observar brazos, flexión y desplazamiento del
cuerpo. Cierre con la X de la ventana. Reinicie el mismo comando para repetir;
cambie `-Semilla` para muestrear otros tiros, manteniendo el modelo y las ganancias.

`Ensayos` en modo headless significa episodios de hasta 150 decisiones, a 50 Hz.
En el visor significa un presupuesto total de `Ensayos * 150` decisiones: una
caída puede provocar un reset anticipado y aumentar el número de episodios.
Los resets del evaluador **no son recuperación física**. Se deshabilitaron las
perturbaciones manuales del mouse para evitar modificar los ensayos accidentalmente.

El backend CPU no alcanza tiempo real en la prueba instrumentada. El viewer
muestra la física calculada, pero puede avanzar más lento que el tiempo real.
No se presenta su render ni la película de reproducción como una métrica de FPS.

## Entorno privado instalado

Python 3.12.10 x64, PyTorch 2.9.0+cpu, torchvision 0.24.0+cpu, mjlab 1.2.0,
MuJoCo y MuJoCo-Warp 3.5.0, Warp 1.12.0 y rsl-rl-lib 5.0.1.
Se agregó SciPy 1.18.1 porque el código importa scipy.interpolate y la resolución
original no lo instalaba. No se cambió ningún archivo del proyecto de referencia.

Para reconstruir únicamente este entorno, con Python 3.12 x64 ya instalado:

```powershell
py -3.12 -m venv validation/keeper_reference4c/.venv-keeper-4c
$python4c = (Resolve-Path validation/keeper_reference4c/.venv-keeper-4c/Scripts/python.exe).Path
& $python4c -m pip install --require-hashes -r app/RoboPenalty/experiments/keeper_reference4c/requirements-cpu.lock
& $python4c -m pip install --require-hashes -r app/RoboPenalty/experiments/keeper_reference4c/requirements-scipy.lock
& $python4c -m pip check
```

No ejecute la creación sobre otro entorno existente. Ambos locks contienen URLs
HTTPS exactas y SHA-256 de ruedas oficiales. No requieren CUDA, toolkit NVIDIA
ni paquetes nvidia. La rueda unificada de Warp anuncia capacidad NVRTC/CUDA en
su banner, pero se ejecuta con device=cpu; PyTorch instalado es CPU.

## Instrumentación y límites de interpretación

- Se reutilizan configuración Eval-Goalkeeper, loader y política originales.
- El único cambio de configuración es aplicar explícitamente la semilla: el
  script original declara ese parámetro pero no lo aplica al entorno.
- Observación del actor: 96 valores por frame, historial de 10 frames. No recibe
  la región objetivo ni los futuros del crítico. No hay memoria LSTM.
- Se registran acciones a 50 Hz y estados/controles/torques a 200 Hz, antes de
  los resets. Las fuerzas de contacto provienen de mujoco_warp.contact_force.
- Se usan IDs canónicos contact.geom. Los campos obsoletos geom1/geom2 del mirror
  no son fiables en esta versión. Las primeras mediciones de contacto se
  conservaron como diagnósticos preliminares y fueron reemplazadas por la corrida 04.
- No se altera qpos, qvel, ctrl, ganancias, contactos ni pesos para medir.
- Ausencia de gol o contacto por sí solos no equivalen a atajada.
- Las dos modalidades originales consumen resets aleatorios en distinto orden:
  no compare el mismo índice de episodio sin comprobar su estado inicial.

Las capturas y la película se producen con render_recording.py a partir de
estados Warp reales guardados. El renderer no integra pasos físicos nuevos.
Los cortes entre episodios no representan una maniobra de recuperación.

## Resultados y pruebas

Consulte EVALUACION_CPU.md para resultados actuales. RESULTADOS.md conserva
la auditoría previa a la instalación, fechada el 30/10/2026.

```powershell
$python4c = (Resolve-Path validation/keeper_reference4c/.venv-keeper-4c/Scripts/python.exe).Path
Push-Location app/RoboPenalty
try {
  & $python4c -X utf8 -B -m unittest experiments.keeper_reference4c.test_observer
  & $python4c -X utf8 -B -m experiments.keeper_reference4c.audit_checkpoint --reference ../../../G1-mjlab-soccer
} finally { Pop-Location }
```

Entorno, cachés, logs, trazas y capturas permanecen bajo `validation/`, excluido
por .gitignore. No se incorporan checkpoints externos al contenido publicable.
La licencia del port no resuelve por sí sola la redistribución de pesos heredados;
se conserva la revisión de procedencia de RESULTADOS.md.
