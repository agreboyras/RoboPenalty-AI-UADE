# Etapa 4A — alcance y primera maniobra de brazos/torso

Fecha: 30/10/2026. Rama de trabajo: `feature/atajadas-arquero`. **Experimento independiente, desactivado por defecto y sin integración en los modos públicos.**

Para observar la maniobra física en una ventana nativa, consultar [Visor interactivo 4A](VISOR_ETAPA4A.md). El visualizador de PNG descrito aquí se conserva para analizar snapshots.

Resultado: movimiento articular real, acotado y reversible, con cobertura adicional en la región alta. **No se demostró una mejora de atajadas en los tiros rodantes actuales.** El arquero continúa soportado por la guía; estos ensayos no demuestran equilibrio libre ni una caída/levantada humana.

## Arquitectura

Código bajo `app/RoboPenalty/experiments/keeper_saves/`:

- `posture_targets.py`: extiende únicamente referencias del PD existente. Conserva Kp=70, Kd=5 y las rampas de 0,6 rad/s y 1,5 rad/s². Usa el mínimo entre los límites de software, control del actuador y fuerza articular del modelo. Cadera roll queda en **88 Nm**, no 139 Nm; muñecas pitch/yaw, en 5 Nm.
- `runtime.py`: adaptador por instancia que sustituye el objeto generador de referencias antes del monitor motor 8C. El bucle histórico sigue escribiendo una sola vez sobre los actuadores del arquero; no hay otro productor de torques. No cambia factories globales.
- `geometry.py`: poses geométricas y distancias convexas en un `MjData` de consulta; no ejecuta pasos físicos ni modifica modelos.
- `metrics.py`: observación posterior al paso, sin escritura sobre motores. Registra articulaciones, referencias, velocidades, torques efectivos, contactos y distancias.
- `run_trial.py`: entrada privada para mapa, ensayo sin interacción con pelota y dos tiros existentes de control.
- `visualize.py`: renders MuJoCo de estados físicos guardados; no genera una animación ni modifica una simulación en vivo.
- `test_experiment.py`: seis pruebas específicas. `bootstrap.py` resuelve los módulos existentes dentro de esta copia.

Si `experimental=False`, el adaptador devuelve directamente las clases estables de portabilidad/8C, sin envolverlas ni modificar el clipping. En el ensayo nominal con `--experimental`, el brazo elegido proviene de la dirección causal que ya calcula `PosturePD` con la predicción B: LEFT/RIGHT indican +/-Y mundial, no el lado anatómico del G1 que mira al delantero. Se conservan predictor, guía, planificador B y retorno de 8C.

La referencia experimental elegida utiliza **media amplitud** de la primera propuesta:

| Articulación del lado de reacción | Postura reactiva estable | Experimental seleccionada |
|---|---:|---:|
| Shoulder roll, magnitud | 0,780 rad | 0,865 rad |
| Shoulder pitch | −0,220 rad | −0,260 rad |
| Elbow | 0,650 rad | 0,525 rad |
| Waist roll, magnitud | 0,035 rad | 0,0575 rad |

No se alteran piernas ni muñecas. En espera central y recuperación se conserva el objetivo estable. Las referencias cambian suavemente; no se escriben `qpos` para ejecutar la maniobra.

## Mapa geométrico: alcance no equivale a ejecución

Se evaluaron siete poses: espera, reacción izquierda/derecha estable y extensiones de media amplitud/completa. Todos los objetivos quedaron dentro de los rangos con margen de 0,02 rad y no produjeron autocolisiones en la consulta estática.

La consulta ubica una esfera del radio físico de la pelota en X=4, con Y muestreado cada **3 cm** y alturas 0,115; 0,4; 0,6; 0,8 y 1 m. Se usa distancia entre las geometrías convexas de colisión de pelota y antebrazos/muñecas. Una intersección geométrica no prueba contacto dinámico ni una atajada. Tampoco constituye el espacio de alcance global del G1: se estudiaron estas poses moderadas y ese plano.

| Pose hacia +Y | Extremo positivo muestreado a Z=1 m | Resultado a Z=0,115 m |
|---|---:|---|
| Reacción estable | +0,45 m | Sin intersección |
| Media amplitud | +0,48 m | Sin intersección |
| Amplitud completa | +0,45 m | Sin intersección |

El resultado es simétrico hacia −Y. La amplitud completa no fue mejor y no se eligió para continuar. A Z=0,8 m algunas extensiones geométricas incluso pierden cobertura en el plano X=4; no se generaliza una ganancia a todas las alturas. No se aumentaron amplitudes para forzar un resultado.

Las envolventes AABB son conservadoras y se etiquetan como tales en los datos. Las pruebas de esfera son consultas distintas y no deben confundirse con aquellas envolventes.

## Ensayo físico sin interacción con pelota

La pelota y el delantero inactivo se colocaron a más de 20 m **antes de comenzar**, en el mismo modelo, para no intervenir en el ensayo. No se borraron cuerpos ni se teletransportaron durante la simulación. La pelvis y la guía siguen restringidas. El delantero usa una postura pasiva de laboratorio, no FreeKick; este caso no representa un penal.

Se compararon estados iniciales idénticos, guardia estable y extensión izquierda/derecha. La consigna temporizada actúa entre 2 y 5 s y luego retorna a la guardia. Es un fixture de seguimiento, **no una decisión autónoma ni una predicción fabricada**. Cada ensayo simula 10 s / 5.000 pasos. Se conservaron los primeros candidatos de amplitud completa y después se probaron ambas direcciones de la variante reducida.

| Medición de variante reducida | Izquierda mundial | Derecha mundial |
|---|---:|---:|
| Cambio real adicional de shoulder roll a 700 ms | 0,1521 rad | 0,1522 rad |
| Cambio real adicional al asentarse | 0,2498 rad | 0,2498 rad |
| Ganancia lateral de envolvente a 700 ms | 3,50 cm | 3,44 cm |
| Ganancia lateral de envolvente al asentarse | 5,26 cm | 5,22 cm |
| Diferencia final máxima respecto de la guardia estable | 0,00348 rad | 0,00349 rad |
| Error máximo de pelvis respecto del soporte | 0 m | 0 m |
| Velocidad articular máxima del ensayo completo | 0,4715 rad/s | 0,4715 rad/s |
| Saturación continua máxima | 0 s | 0 s |
| Autocontactos detectados | 0 | 0 |

La velocidad máxima incluye el establecimiento inicial de la guardia, no solo la extensión. El error final respecto de la propia pose previa fue aproximadamente 0,012 rad, similar al asentamiento de la guardia de referencia. El criterio de retorno se fijó en 0,03 rad antes del ensayo; no se relajó para aceptar los resultados.

En los **estados realmente ejecutados** a 700 ms, la consulta de esfera a Z=0,8 m pasa de un extremo Y=0,39 a 0,42 m; se gana una celda de 3 cm. A Z=1 m aparece cobertura geométrica adicional que la guardia sin reacción no tenía. Esto es evidencia de alcance corporal ejecutado en la región alta, no de una atajada comprobada. A la altura de los tiros nominales sigue sin haber intersección.

La comparación con la reacción estable durante un tiro está en la sección siguiente; la guardia de referencia de este laboratorio no debe confundirse con la reacción izquierda/derecha que ya realiza el arquero B.

Se repitió la maniobra reducida izquierda con el mismo código y condiciones: posiciones, velocidades, torques, referencias y snapshots fueron exactamente iguales. Solo difieren los tiempos reales. No se declara robustez global frente a perturbaciones.

## Dos tiros físicos de control

Solo se avanzó después de pasar los ensayos sin pelota. Se usaron dos acciones existentes, sin cambiar bias, pelota, policy ni condiciones iniciales. El brazo se eligió a partir de observaciones/predicciones actuales, sin recibir el identificador del tiro.

| Acción | Postura estable | Experimental | Menor separación muestreada pelota–antebrazos/muñecas | Contacto positivo de brazos |
|---|---|---|---:|---:|
| `right_inter_m080` | Gol | Gol | 0,620 m | 0 |
| `left_near_b060` | Atajada | Atajada | 0,537 m | 0 |

La atajada experimental de centro-izquierda fue contacto con `gk/geom_031`, en el pie/tobillo: primer contacto a 5,044 s, fuerza normal aproximada de 85,15 N. **No fue una atajada de brazo.** Ambos ensayos terminaron en DONE, sin autocolisiones, saturaciones persistentes ni violaciones de torque. La velocidad articular máxima fue 0,577 y 2,259 rad/s, respectivamente, por debajo del control existente de 3 rad/s.

Las diferencias del arquero con la opción activada son intencionales: no se exige identidad de sus estados físicos con la postura estable. No se demostró aumento de atajadas y no se ajustó la clasificación para presentarlo como mejora.

## Evidencia visual y registros

Los PNG son capturas reales del Renderer MuJoCo de snapshots de los ensayos físicos. Se aplican a un `MjData` de reproducción fuera de la simulación en vivo; el render no ejecuta pasos físicos. Se reutiliza el estadio 7D y la publicidad V2 sin modificar sus archivos. La cámara cercana es solo diagnóstica.

| Guardia estable | Extensión izquierda | Extensión derecha |
|---|---|---|
| [Captura](images/keeper_saves_4a/stable.png) | [Captura](images/keeper_saves_4a/left.png) | [Captura](images/keeper_saves_4a/right.png) |

- [Movimiento alcanzado a 700 ms](images/keeper_saves_4a/available_700ms.png).
- [Recuperación](images/keeper_saves_4a/recovery.png).
- [Serie temporal articular CSV](data/keeper_saves_4a.csv): consigna, posición, velocidad y torque real, con referencia estable.

Los JSON completos registran las 29 articulaciones a 50 Hz, snapshots y límites. El monitor de saturación y contactos trabaja a 500 Hz. Se define saturación persistente como al menos 0,1 s continuos al 98% del límite efectivo. Las fuerzas de contacto se leen del paso calculado; la telemetría posterior a `mj_step` combina posiciones articulares integradas con el caché cinemático de ese paso, de 2 ms. Las distancias se muestrean a 50 Hz: no se presentan como un mínimo continuo exacto. Los mapas de esfera usan `mj_forward` sobre datos auxiliares.

## Regresión e integridad

- **176 tests existentes aprobados y seis tests experimentales aprobados**, ejecutados separadamente. No se modificó el runner estable.
- Tanda pública automática, semilla 2026: **3 goles, 2 atajadas, 0 errados, 35.000 pasos**; 52,291 s de sesión y 59,358 s de proceso en esta ejecución.
- Cero diferencias en los estados iniciales/finales, trazas, contactos, decisiones, planificación, postura, retorno, monitor motor y aprendizaje registrados respecto de la validación nominal anterior de 8C.
- Un ensayo nominal privado sin `--experimental` también coincidió exactamente con el episodio estable equivalente. No se sustituye el controlador cuando la opción está desactivada.
- No se modificaron 8C, predictor, B, guía, recuperación, 7D, publicidad, audio, XML, ONNX ni NPZ. Los 104 recursos de la copia usada y los archivos/calibraciones de 8C conservaron sus SHA-256.
- `main` conserva el commit `fa05394e1ce69f01cd3b1eb2e85edd43ab34d457`. No se hizo add, commit ni push.

El alcance de identidad son los registros disponibles, no cada estado intermedio no guardado. Se excluyen tiempos reales, rutas y objetos de proceso. La prueba se hizo en otra copia dentro de `validation/keeper_saves_4a_20261030/` usando un entorno ya instalado; no es una nueva validación de instalación en otra computadora. Los avisos de Hydra preexistentes permanecen.

## Reproducir el experimento

Requiere una instalación local completa de 104/104 recursos. No instala ni obtiene recursos nuevos. Desde la raíz del paquete:

```powershell
Set-Location app\RoboPenalty
& ..\..\.venv\Scripts\python.exe -X utf8 -E -s -B -m experiments.keeper_saves.test_experiment

# Mapa geométrico: cero pasos físicos.
& ..\..\.venv\Scripts\python.exe -X utf8 -E -s -B -m experiments.keeper_saves.run_trial --case map --output experiments/keeper_saves/results/map_01.json

# Guardia de referencia y maniobra izquierda. Elegir salidas nuevas.
& ..\..\.venv\Scripts\python.exe -X utf8 -E -s -B -m experiments.keeper_saves.run_trial --case no-ball --side LEFT --output experiments/keeper_saves/results/stable_01.json
& ..\..\.venv\Scripts\python.exe -X utf8 -E -s -B -m experiments.keeper_saves.run_trial --case no-ball --side LEFT --experimental --output experiments/keeper_saves/results/left_01.json

# Solo después de revisar passed=true y las métricas de la prueba sin pelota:
& ..\..\.venv\Scripts\python.exe -X utf8 -E -s -B -m experiments.keeper_saves.run_trial --case nominal --action right_inter_m080 --experimental --output experiments/keeper_saves/results/ball_01/physical.json

# Reproducir visualmente los estados medidos, sin lanzar una partida:
& ..\..\.venv\Scripts\python.exe -X utf8 -E -s -B -m experiments.keeper_saves.visualize --trial experiments/keeper_saves/results/left_01.json --output experiments/keeper_saves/results/images_left_01
```

Para la derecha usar `--side RIGHT`; el otro tiro de control fue `left_near_b060`. Los destinos deben ser nuevos: se rechaza sobrescribir resultados. El modo `no-ball` siempre utiliza condiciones iniciales de laboratorio con pelota apartada, incluso sin `--experimental`; la prueba de equivalencia nominal es el caso `nominal` y la tanda pública, no ese laboratorio.

## Recomendación

Conservar la maniobra como experimento: es estable bajo el soporte actual, reversible y produce alcance adicional medido. **No promoverla como mejora del arquero para el catálogo rasante.** Antes de una maniobra reactiva más amplia, conviene un ensayo físico con pelota a altura compatible que compruebe contacto y desvío reales, identificado como prueba de laboratorio y sin cambiar los cinco tiros.

Si el objetivo es detener específicamente las esquinas inferiores actuales, ampliar brazos no está respaldado por estos datos. Una variante de base con otros grados de libertad merece una investigación independiente, con aprobación expresa y nuevos controles de equilibrio/aterrizaje; quitar la guía no garantiza una atajada ni recuperación. No se implementaron caídas, saltos ni un arquero libre.

Código nuevo bajo `experiments/keeper_saves/`; datos completos y candidatos iniciales quedan en `validation/keeper_saves_4a_20261030/`, excluidos de Git. Los resultados que produzca el usuario en `experiments/keeper_saves/results/` también están excluidos. El inventario público se actualiza para el código, este informe, CSV e imágenes propios; no cambia los hashes históricos de recursos.
