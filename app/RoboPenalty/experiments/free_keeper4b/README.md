# 4B: primer ensayo de equilibrio libre

Experimento privado e independiente. No modifica ni se importa desde 8C, 9A,
7D o 4A. No contiene checkpoints. El Deploy externo se abre solo para lectura;
sus permisos pendientes no se presentan como autorización de redistribución.

## Contrato verificado antes de simular

- Checkpoint externo `policy/loco_mode/model/policy_29dof.pt`, SHA-256
  `d1d91b0201beeb649a4624ba40052d10fe4aebe98bf6f4847decf75dd1fee2da`.
- Configuraciones externas fijadas mediante SHA-256 de su texto LF canónico.
  Solo se admite LF/CRLF para estos YAML; el checkpoint exige bytes exactos.
- Observación float32: velocidad angular corporal (3), gravedad corporal (3),
  velocidad deseada física cero (3), q relativa en orden de política (29),
  dq en ese orden (29), última acción cruda (29). Escalas del YAML original.
- Se ejecuta el TorchScript completo: normalizador original en eval, LSTM
  unidireccional de una capa, estados h/c de forma (1,1,256), actor de 29 salidas.
  No se construye un historial adicional ni se normaliza dos veces.
- Calentamiento de 50 inferencias sin física. Después se ponen h/c y última
  acción a cero explícitamente. Se comprueba máximo absoluto cero en cada ensayo.
  Se comprueba también que los buffers del normalizador no cambian.
- Referencias `default_angles + 0.25*acción`, con los clips originales de entrada
  y salida ±100. Reordenamiento conforme al YAML y nombres de motores verificados.
- PD con kp/kd originales, cada 2 ms; política cada 20 ms. Los torques de origen
  se toman de `deploy_mujoco/config/mujoco.yaml`: el campo tau_limit de LocoMode
  no es utilizado por su ejecutor original. Se impone además el mínimo de límites
  compilados de control, fuerza de actuador y fuerza articular (gear 1).
- Protección explícita: referencias articulares recortadas al rango del modelo;
  se registra cuántas referencias necesitaron ese recorte. Esto es una protección
  del experimento, no una afirmación de identidad del comportamiento con Deploy.

## Escena e inicialización

MjSpec carga el XML Unitree original incluido, conserva su raíz libre y los
29 motores. Añade únicamente suelo plano (fricción 1/0.005/0.0001) y una luz.
No hay carro, igualdad, apoyo de pelvis ni fuerza de equilibrio. Gravedad por
defecto de MuJoCo y dt 0.002 s. El suelo es propio de este ensayo, no una
modificación del suelo de la partida.

La postura inicial utiliza los ángulos de la política. Antes del primer paso,
la base se coloca de modo que las ocho esferas de pies tengan al menos 1 mm de
separación del suelo. Se registra la altura resultante. Después de inicializar
no se escribe qpos/qvel: todo movimiento procede de mj_step y torques articulares.

## Criterios fijados antes del primer ensayo

5000 pasos / 500 decisiones / 10 s, sin caída (pelvis no inferior a 0.50 m),
roll y pitch absolutos menores de 15°, deriva horizontal menor de 0.10 m,
sin contactos salvo pies-suelo, sin violaciones de límites articulares
(tolerancia numérica 1e-6 rad), sin saturación continua de ningún motor de
0.10 s o más, estados finitos, normalizador congelado y ausencia de fuerzas
externas. Las advertencias de MuJoCo también impiden declarar éxito.

Una caída no reinicia el robot: se conservan los 5000 pasos si los estados
siguen siendo finitos. El ensayo solo se interrumpe por cierre del visor,
fuerza externa detectada o estados no finitos. No se cambian los criterios
después de observar el resultado.

## Ejecución desde la raíz de RoboPenalty-AI-Complete

```powershell
.\scripts\probar_equilibrio_4b.ps1 -DeployPath "..\RoboNaldo_Deploy"
.\scripts\probar_equilibrio_4b.ps1 -DeployPath "..\RoboNaldo_Deploy" -Viewer -Repeticiones 1
```

El Python predeterminado es `validation/keeper_balance4b/.venv/Scripts/python.exe`.
También se admite `-Python "ruta\al\python.exe"`, que debe contener torch CPU,
numpy, PyYAML y mujoco. No es necesario completar los 104 recursos de la partida.

El entorno privado de esta instalación ya fue preparado con autorización.
Para recrearlo en otra carpeta con Python 3.12 x64 disponible como `python`:

```powershell
python -m venv .\validation\keeper_balance4b\.venv
& .\validation\keeper_balance4b\.venv\Scripts\python.exe -m pip install torch==2.9.0 --index-url https://download.pytorch.org/whl/cpu
& .\validation\keeper_balance4b\.venv\Scripts\python.exe -m pip install mujoco==3.13.0 numpy==2.5.3 PyYAML==6.0.3
```

Esto instala dependencias del ensayo; no descarga la política externa.

El visor ejecuta la misma física en vivo, con pacing de tiempo real. Si el equipo
no alcanza esa velocidad, el ensayo tarda más: no se omiten pasos ni se acelera
la física. Cerrar con la X termina el ensayo sin reiniciarlo; si se cierra antes
de 10 s queda incompleto. No arrastrar el robot con el mouse: una fuerza externa
invalida el ensayo. No hay controles de tiros, saltos ni maniobras nuevas.

## Evidencia y códigos de salida

Cada ejecución crea un directorio nuevo en `validation/keeper_balance4b`, ya
excluido de publicación. Cada repetición guarda `summary.json`, `trace.npz`
y `contacts.jsonl`. `comparison.json` compara hashes de las trazas físicas
completas y decisiones, excluyendo tiempos de pared. Nunca sobrescribe ensayos.

La traza contiene tiempos, qpos/qvel, torque solicitado, control limitado,
torque articular aplicado, referencias, ángulos y contactos. Las columnas se
describen en summary.json; los registros por paso son previos a la integración.
El estado final se guarda por separado. Se registran distancias de contacto,
fuerzas y penetración máxima, sin filtrar autocolisiones.

Código 0: criterios superados. Código 2: prueba física no superada. Un resultado
negativo es evidencia válida; no equivale a error del lanzador.

```powershell
Push-Location .\app\RoboPenalty
& ..\..\validation\keeper_balance4b\.venv\Scripts\python.exe -B -m unittest experiments.free_keeper4b.test_balance -v
Pop-Location
```

Para verificar el checkpoint real, desde `app/RoboPenalty`:

```powershell
& ..\..\validation\keeper_balance4b\.venv\Scripts\python.exe -B -m experiments.free_keeper4b.test_checkpoint --deploy "..\..\..\RoboNaldo_Deploy" -v
```

Las capturas pueden reproducirse con el renderizador MuJoCo a partir de la
traza, sin integrar pasos físicos nuevos. Desde `app/RoboPenalty`:

```powershell
& ..\..\validation\keeper_balance4b\.venv\Scripts\python.exe -B -m experiments.free_keeper4b.render_trace --deploy "..\..\..\RoboNaldo_Deploy" --trial "..\..\validation\keeper_balance4b\headless_01\trial_01" --output "..\..\validation\keeper_balance4b\capturas_nuevas"
```

La salida debe ser una carpeta nueva. `initial.png` y `final.png` muestran
estados registrados, sin interpolación ni corrección de postura.

Superar este ensayo solo demostraría equilibrio nominal sin pelota durante
10 segundos. No demostraría robustez a empujes, salto, caída ni atajada.
