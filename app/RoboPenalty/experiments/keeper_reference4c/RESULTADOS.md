> Documento histórico de la auditoría del 30/10/2026, anterior a la instalación.
> La ejecución Windows/CPU ya fue realizada; ver [EVALUACION_CPU.md](EVALUACION_CPU.md).
> Los bloqueos y conclusiones pendientes de este documento corresponden a aquella fecha.

# Etapa 4C: compatibilidad neural confirmada; ejecución física pendiente

Fecha: 30/10/2026. RoboPenalty: rama `feature/atajadas-arquero`.
Referencia local G1-mjlab-soccer: commit `96cfa02a6acea17dd9e01f821f8937fc6ea67988`,
sin cambios tracked al revisar. No se modificó ese proyecto ni se instalaron paquetes.

**Estado: Fase 1 auditada. Fases física y visual bloqueadas por falta de un
entorno de dependencias compatible. No se considera evaluada la naturalidad.**

## Procedimiento original localizado

`G1-mjlab-soccer/scripts/eval_naive_goalkeeper.py` registra `Eval-Goalkeeper`,
carga su configuración, crea ManagerBasedRlEnv y usa GoalkeeperRunner.
Sin `--checkpoint` ejecuta un agente cero: no evalúa goalkeeper.pt.
`--viewer native` selecciona NativeMujocoViewer; `auto` en Windows puede elegir
Viser porque decide a partir de DISPLAY/WAYLAND_DISPLAY. No hace falta inventar
un visor distinto antes de comprobar el original.

La invocación original `--help` con el Python privado existente falló realmente
en `import tyro`, con `ModuleNotFoundError`. No llegó a crear el mundo físico.

## Entorno, versiones y alternativas

| Componente | Referencia local | Disponible en entorno 4B |
|---|---|---|
| mjlab | 1.2.0 | No |
| mujoco-warp | 3.5.0 | No |
| MuJoCo | 3.5.0 | 3.13.0; versión diferente |
| Torch | mjlab requiere >=2.7.0 | 2.9.0+cpu |
| warp-lang | mjlab requiere >=1.12.0 | No |
| rsl-rl-lib | mjlab fija 5.0.1 | No |
| tyro / tensordict / viser | Requeridos por evaluador/framework | No |

La guía local recomienda Ubuntu 22.04, NVIDIA y Python 3.11. La metadata de
mjlab 1.2.0 admite Python >=3.10,<3.14 y extra CPU; su simulador tiene una ruta
CPU sin CUDA graphs. La CPU de Windows es una posibilidad técnica, **no una
ejecución validada**. GPU consultada: AMD Radeon 610M; no hay dispositivo CUDA
disponible en el Torch instalado. WSL no está instalado y no se instaló.

Fuentes versionadas:
- https://github.com/mujocolab/mjlab/blob/v1.2.0/pyproject.toml
- https://github.com/mujocolab/mjlab/blob/v1.2.0/src/mjlab/sim/sim.py
- Guía local: `G1-mjlab-soccer/doc/setup_en.md`.

Recomendación: solicitar autorización para un entorno CPU privado nuevo,
con el stack fijado por la referencia y sin cambiar el entorno 4B. Primero
probar importación, compilación y diez decisiones, luego un episodio y el visor.
Si CPU Windows no funciona fielmente, usar una máquina Linux/NVIDIA con el
mismo checkout y configuración. No portar la política al runtime 8C para salvar
este bloqueo ni sustituir MuJoCo Warp por otro ejecutor presentado como equivalente.

## Modelo y control configurados, todavía no compilados en mjlab

Modelo `src/assets/robots/unitree_g1/xmls/g1.xml`: `g1_29dof_rev_1_0`,
raíz libre y 29 articulaciones. Los 35 meshes declarados están disponibles.
El framework crea los actuadores; compilar solo el XML no reproduce el runtime.

- Pelvis inicial (0,0,0.8), yaw=0; G1 mira +X, pelota llega desde +X.
- Pose específica GK: hip_pitch -0.1, hip_roll ±0.2, knee 0.3,
  ankle_pitch -0.2, ankle_roll ∓0.2; shoulder_roll ±0.5, elbow 1.2 rad;
  cintura y muñecas en cero. No es el HOME_KEYFRAME general.
- Ganancias kp/kd: caderas 150/2, rodillas 300/4, tobillos 40/2,
  cintura y hombros/codos 150/2, muñecas 20/0.5.
- Límites de esfuerzo configurados: hip pitch/yaw 88 Nm; hip roll y rodilla
  139 Nm; tobillos y cintura pitch/roll 50 Nm; hombros/codos y muñeca roll 25 Nm;
  muñeca pitch/yaw 5 Nm. Deben confirmarse en el modelo compilado antes de medir.
- Armature/inercia reflejada específica de los motores. Factor soft joint limit 0.9.
- Siete cápsulas por pie, condim 3, fricción 0.6; otras colisiones condim 1,
  incluyendo autocolisiones según FULL_COLLISION. No son los pies de 4B.
- Incluye cápsulas físicas `left_hand_collision` y `right_hand_collision`,
  radio 0.035 m, además de muñecas/antebrazos. No son solo las mallas visuales
  de manos del G1 anterior. Su efectividad con pelota todavía no fue medida.
- Los postes y travesaño de referencia son colisionables. Un rebote en el arco
  no es evidencia de una atajada del robot.
- Física 200 Hz (dt 0.005), control 50 Hz (decimation 4), episodios de 3 s;
  solver iterations 10, ls_iterations 20, capacidad de contactos eval 128.

Son valores declarados en configuración, no mediciones de estabilidad.

## Checkpoint y observaciones: pruebas realmente ejecutadas

SHA-256 del checkpoint externo:
`7ecdedff5de6e30a0a4d11742561a9be6c94d8faeefc4701f3e8788381b67b14`.

Con Torch CPU existente se cargó con `weights_only=True` y se instanció la clase
local sin requerir mjlab. **Carga strict=True completa: todas las claves y formas
coinciden**, incluidos actor, crítico y estimadores. Inferencia CPU con entrada
de prueba produce 29 acciones finitas. La reordenación del historial se comprobó
con entradas etiquetadas. Esto no ejecuta física ni representa una atajada.

El probe reproducible `audit_checkpoint.py` aprobó seis comprobaciones: claves
estrictas, forma/valores finitos, orden del historial, determinismo con la misma
entrada, ausencia de estado recurrente y conservación de hashes externos.
Evidencia local: `validation/keeper_reference4c/audit_01.json`.

Actor: 10 marcos ×96 valores =960, con posición actual de pelota en marco de
pelvis (3), velocidad angular corporal ×0.25 (3), gravedad proyectada (3), q
relativa a pose GK (29), dq×0.05 (29) y acción cruda anterior (29). Se transpone
historial term-major de mjlab a frame-major del checkpoint. Sin normalizador
estadístico adicional. La salida usa offset GK +0.25×acción, con clip externo
de acción ±100 en el wrapper original.

No tiene LSTM: `is_recurrent=False` y reset del actor no hace nada. El historial
se reinicia en ObservationManager, junto con ActionManager al reiniciar entorno.
En mjlab 1.2.0 la primera observación tras reset rellena todo el historial de
esa fila; no debe sustituirse por diez ceros.

El actor usa estimadores aprendidos de pelota/región a partir del historial.
No recibe la etiqueta real de región ni el punto final futuro del tiro. El
crítico sí agrega velocidad lineal, velocidad de pelota y datos privilegiados
como región y objetivo final; no deben suministrarse a la inferencia del actor.

Fuentes de reset:
- https://github.com/mujocolab/mjlab/blob/v1.2.0/src/mjlab/managers/observation_manager.py
- https://github.com/mujocolab/mjlab/blob/v1.2.0/src/mjlab/utils/buffers/circular_buffer.py

## Tiros y limitaciones de las métricas originales

`goalkeeper_ball_reset.py` asigna posición y velocidad inicial de pelota mediante
un lanzamiento parabólico; no hay delantero ni contacto pie-pelota en esta prueba.
Inicio X=3..5 m, Y=-1.5..1.5 m, Z=0.1..1.5 m; objetivo X=-0.6..-0.1 m,
con seis regiones laterales y de altura; tiempo de vuelo 0.6..1.0 s. Pelota radio
0.10 m, masa 0.35 kg y arrastre activado. No son los tiros rasantes de RoboPenalty.
El arco de evaluación está en X=-0.5, ancho 3 m, alto 1.8 m.

Hallazgos que deben resolverse mediante instrumentación externa justificada:

1. El evaluador usa `load_state_dict(..., strict=False)` y no informa claves
   omitidas. La auditoría independiente sí confirmó todas las claves con strict.
2. `blocked = not ball_entered_goal`: cuenta también tiros errados y episodios
   terminados sin gol. No exige contacto. No es una tasa demostrada de atajadas.
3. El helper de gol mira una posición muestreada a 50 Hz, sin interpolación ni
   prueba de causalidad de contacto. El entorno mjlab puede auto-reiniciarse antes
   de devolver el estado de un paso terminal; es necesario capturar el evento
   antes del reset. Caídas se terminan al superar 70° de orientación configurada.
4. El campo CLI `seed` está declarado pero no se aplica en el script revisado.
   Pasar `--seed 2810` no demuestra que esa semilla gobierne los tiros.
5. El script no registra las métricas de penetración, saturación y recuperación
   solicitadas por RoboPenalty ni demuestra que un contacto evite un gol.

Fuentes:
- `G1-mjlab-soccer/scripts/eval_naive_goalkeeper.py`
- https://github.com/mujocolab/mjlab/blob/v1.2.0/src/mjlab/envs/manager_based_rl_env.py
- https://github.com/mujocolab/mjlab/blob/v1.2.0/src/mjlab/rl/vecenv_wrapper.py

La instrumentación propuesta viviría fuera del proyecto de referencia, sin
cambiar su modelo, acciones ni ganancias: registrar pasos físicos y contactos,
cruce del arco, terminales antes del reset, límites y postura, y fijar la semilla
efectivamente. No está implementada ni autorizada como modificación de referencia.

## Licencias y procedencia

G1-mjlab-soccer declara Apache-2.0 en LICENCE y reconoce derivación de
Humanoid-Goalkeeper. El proyecto original declara su código bajo CC BY-NC-SA 4.0.
La licencia del port no demuestra por sí sola el alcance de redistribución del
checkpoint y movimientos heredados. No se copiaron pesos ni se conceden permisos
por acceso público. Esta revisión no resuelve la cadena de titularidad de cada peso.

- https://github.com/liujy25/G1-mjlab-soccer
- https://github.com/InternRobotics/Humanoid-Goalkeeper#-license

Además, el proyecto original usa Isaac Gym: evaluar fielmente el port local de
MuJoCo Warp no equivale a reproducir idénticamente el simulador de entrenamiento.

## Conclusión y pendientes

Compatible a nivel neural; ejecución física y naturalidad **no comprobadas**.
No hay contactos, atajadas, caídas ni tiempos de simulación medidos para 4C;
no se generó evidencia visual. No se recomienda integrar ni descartar la política
por estos resultados de inferencia. Se necesita autorizar el entorno aislado y
ver funcionar el evaluador nativo, con métricas independientes, antes de decidir.
