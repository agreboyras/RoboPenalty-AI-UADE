# Etapa 4C: evaluación física Windows/CPU

Fecha: 31/10/2026. Rama feature/atajadas-arquero.

**Viabilidad técnica demostrada en el port local de referencia; integración no
aprobada.** El visor nativo se abrió, ejecutó pasos reales y cerró por presupuesto.
La evaluación personal del usuario sobre la naturalidad sigue pendiente.
No se ejecutó una atajada equivalente dentro del estadio de RoboPenalty.

## Instalación y contrato

Entorno independiente: `validation/keeper_reference4c/.venv-keeper-4c`.
Python 3.12.10 x64, torch 2.9.0+cpu, torchvision 0.24.0+cpu, mjlab 1.2.0,
mujoco 3.5.0, mujoco-warp 3.5.0, warp-lang 1.12.0, rsl-rl-lib 5.0.1.
Resolución de 124 paquetes fijados por rueda HTTPS y SHA-256. Se agregó SciPy
1.18.1, dependencia no declarada que requiere scipy.interpolate en la referencia;
el total resuelto es 125 paquetes, más pip. No se parcheó código externo.
`pip check`: No broken requirements found. Freeze y reportes completos privados.

No se instaló toolkit CUDA ni paquetes nvidia/cupy/triton. Torch no tiene CUDA.
La rueda unificada Warp incluye capacidad CUDA/NVRTC y la anuncia al iniciar;
no hay driver/dispositivo CUDA disponible y todos los ensayos usan device=cpu.
Cachés, temporales y W&B deshabilitado se configuran solo en los procesos privados.
La consola se inicia con -X utf8 para evitar un error cp1252 al imprimir el
resumen original. Ninguno de estos ajustes cambia la física o la política.

Referencia externa sin cambios: G1-mjlab-soccer, revisión
`96cfa02a6acea17dd9e01f821f8937fc6ea67988`.
Checkpoint externo: src/assets/soccer/weight/goalkeeper.pt.
SHA-256: `7ecdedff5de6e30a0a4d11742561a9be6c94d8faeefc4701f3e8788381b67b14`.

Carga estricta de todas las claves, salida 29 finita y determinista. El historial
96×10 se reordena según el actor original. No hay LSTM ni normalizador running.
La inferencia no cambia al modificar exclusivamente las entradas del crítico:
no se usa su información privilegiada para elegir acciones. Siete comprobaciones
neurales aprobadas en audit_02.json.

Mundo original Eval-Goalkeeper: raíz libre, 29 actuadores, nq=43, nv=41,
paso físico 0.005 s (200 Hz), decisiones 50 Hz, episodios de hasta 3 s. Se conserva
la escala articular 0.25, ganancias, límites, contactos y configuración de tiros.
El orden natural de acciones se comprobó contra ActionManager, no contra la
numeración agrupada de motores. Modelo compilado completo en model.json.
El flag de drag del código no implica aire efectivo: density=0 y viscosity=0
son los valores reales compilados. No se corrigieron para favorecer el resultado.

Los tiros se inicializan con el generador parabólico original. No hay delantero,
FreeKick ni manipulación posterior de pelota por nuestro observador. Se aplica
explícitamente seed=2810: el CLI original declara seed, pero no lo transmite.
El evaluador original, sin instrumentación propia, también completó un episodio.

## Cinco episodios físicos instrumentados

Corrida válida: observed_headless_04, semilla 2810. Cruce interpolado por X=-0.5,
criterio de centro dentro de |Y|<=1.5 y 0<=Z<=1.8, a resolución física de 5 ms.
Contacto exige fuerza normal >0.001 N del solver Warp, no proximidad visual.

| Episodio | Simulado s | Real s* | Primer contacto s | Inclinación máx. ° | Penetración global mm | Pasos con saturación | Resultado |
|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 1.68 | 7.61 | 0.760 | 72.35 | 29.46 | 101 | Gol con contacto |
| 2 | 3.00 | 14.86 | 0.685 | 8.23 | 26.50 | 2 | Bloqueo con rebote; sin gol observado |
| 3 | 1.98 | 10.39 | 0.625 | 85.46 | 46.34 | 70 | Gol con contacto |
| 4 | 1.94 | 10.17 | 0.660 | 82.70 | 31.60 | 24 | Contacto sin gol; atajada no probada |
| 5 | 2.20 | 14.10 | 0.840 | 84.18 | 42.38 | 15 | Contacto sin gol; atajada no probada |

*Tiempo del episodio instrumentado, incluyendo observación y escritura de sus
resultados, excluyendo carga inicial y compilación JIT. Total: 2160 pasos,
10.80 s simulados y 57.12 s reales. No es tiempo del controlador solo ni FPS.
No se aisló el tiempo de inicialización. La ejecución no alcanza tiempo real.

Hay contacto físico pelota–robot en los cinco episodios, dos goles y tres
no-goles observados. **No equivale a tres atajadas.**

- Episodio 1: contacto de muñeca derecha, pero gol a t≈1.000 s, Y=-1.090,
  Z=1.530. Episodio 3: contactos de brazo/torso y gol a t≈1.605 s,
  Y=-0.733, Z=0.098. El contacto por sí solo no evita el gol.
- Episodio 2: primer impacto con torso a t≈0.685 s, seguido de contactos de
  brazos/cadera/pelvis y reversión longitudinal. La extrapolación balística
  inmediatamente anterior al contacto apuntaba dentro del arco con margen;
  no hay cruce durante los 3 s. Evidencia de bloqueo corporal, limitada a esta
  ventana; no se atribuye a una palma ni se demuestra recuperación de pie.
- Episodio 4: contacto de muñeca y cruce por fuera en Y=-2.107. No se atribuye
  automáticamente el tiro fuera a una atajada. Episodio 5: contactos de muñeca,
  sin cruce antes de terminar por inclinación; causalidad de atajada no probada.

Cuatro episodios superan 70°, umbral de terminación por orientación de la
referencia. Son terminaciones por caída/inclinación, no recuperación demostrada.
El segundo baja la pelvis hasta 0.452 m y se mantiene por debajo de 8.24°.
Se observan brazos, torso, flexión y desplazamientos amplios: es mucho menos rígido
que el arquero guiado, pero no hay todavía evidencia de una zambullida estable con
recuperación. Máximo torque observado 139 Nm, con recortes al límite efectivo.
Las saturaciones se expresan como pasos con al menos un actuador al límite;
no se investigó aquí su duración por articulación. Penetración máxima global
46.34 mm. Las articulaciones también exceden límites blandos en dinámica:
ver joint_limit_analysis.json. No hubo NaN ni overflow de buffers.

## Corrección del observador y reproducibilidad

Las corridas 01–03 se conservan como diagnósticos preliminares. Inicialmente se
leyeron geom1/geom2, campos obsoletos del mirror MjData, y se informó erróneamente
cero contactos de robot. MuJoCo-Warp 3.5 copia contact.geom. Se corrigió el
observador, se probó regresión explícita de ese caso y se verificaron fuerzas con
la API nativa mujoco_warp.contact_force. En corrida 04 ambas lecturas de fuerza
coinciden para los contactos medidos. El error era de instrumentación propia,
no de la política. No usar los conteos preliminares como resultados físicos.

Los cinco episodios 01 y 04 coinciden exactamente en cada elemento de frames
(tiempo, qpos, qvel, ctrl y fuerza de actuadores), acciones e inicialización.
Esto confirma que el cambio de medición no modificó los estados/control registrados.
Archivo: contact_correction_trace_comparison.json.

## Visor original y evidencia visual

NativeMujocoViewer funcionó en Windows con el backend físico CPU. Prueba 01:
1200 subpasos, 6 s simulados, cierre por presupuesto. Prueba 02 con contactos
corregidos: 600 subpasos, 3 s simulados, 28.81 s de episodio instrumentado;
contactos de brazo derecho con rebote y sin gol observado. No se atribuye la
diferencia de tiempo solo al render: incluye sincronización y observación.
No hay métrica fiable de FPS. No se probó interacción humana de cámara/cierre X,
aunque el viewer cerró y liberó recursos al terminar su presupuesto.

El orden de resets consume números aleatorios de manera distinta en headless y
viewer originales. El episodio 1 headless y el 2 del viewer01 tienen el mismo
estado inicial y trazas/acciones exactamente iguales. El episodio 1 viewer01 y
viewer02 también coinciden exactamente, tras corregir la lectura de contactos.
No se afirma equivalencia de todos los índices de ambos modos.

Capturas reales y película: validation/keeper_reference4c/captures_02/.
Se renderizan estados Warp registrados, sin integrar una segunda simulación.
La película va a 50 frames/s de tiempo simulado; eso no mide fluidez del visor.
Los cortes entre episodios son resets, no una recuperación física.

## Validaciones y preservación

- 176 tests de regresión públicos/core: aprobados, sin alterar los tests.
- 5 tests propios del observador: aprobados.
- 7 comprobaciones neurales y 7 comprobaciones de entorno: aprobadas.
- pip check: aprobado. Parse de PowerShell del lanzador: sin errores.
- 641 archivos previos de app/ y referencia: mismos SHA-256 antes/después.
- Referencia G1-mjlab-soccer limpia; rama principal de trabajo sigue siendo
  feature/atajadas-arquero. No se hizo add, commit, push ni cambios de rama.
- Entorno, trazas y capturas bajo validation/ están excluidos por Git.
- No se repitió una tanda pública de RoboPenalty en esta etapa: no se atribuye
  a esta evaluación una nueva validación física de sus cinco penales.

## Archivos de esta iteración

Dentro de experiments/keeper_reference4c: environment.py, original_entry.py,
observe_reference.py, render_recording.py, test_observer.py, requirements-cpu.lock,
requirements-scipy.lock y este informe. Se actualizaron audit_checkpoint.py,
README.md y una nota cronológica en RESULTADOS.md. Se agregó el lanzador privado
scripts/evaluar_arquero_4c.ps1. No se modificaron fases estables ni referencias.

## Recomendación

Observar primero los movimientos con el comando de README.md y la película.
No integrar todavía. Hay ejecución fiel del port local, contactos y reacción
corporal real, pero la estabilidad/recuperación no quedan demostradas y existe
penetración relevante. No atribuir estos fallos a CPU sin una comparación de
backend controlada. Si se continúa, la siguiente investigación debe contrastar
el port MuJoCo-Warp con el contrato y entorno de entrenamiento Isaac Gym,
con autorización específica antes de nuevas dependencias o cambios físicos.
La cadena de permisos de los pesos permanece pendiente según la auditoría
histórica; no se copiaron ni se habilitó su redistribución.
