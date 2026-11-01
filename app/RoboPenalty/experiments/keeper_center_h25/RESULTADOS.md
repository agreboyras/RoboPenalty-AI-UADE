# Resultados del Hito 2.5

Fecha: 2026-10-31. **PARCIAL**, no aptitud de atajada demostrada.

## Protocolo y controles

Todos los ensayos completos: 3000 pasos, 6 s simulados, dt=0.002 s. Misma composición libre H1, 58 actuadores, sin slider ni sostén externo. Misma posición inicial centrada y orientación hacia el delantero. Referencias finales limitadas por el modelo; un único PD del arquero, mismos límites efectivos y ganancias. Inferencia de equilibrio hasta 1.98 s, transferencia a t=2 s sin salto de referencia. El observador verificó que no cambia qpos, qvel, ctrl ni fuerzas externas.

Se conservaron los criterios H2: velocidad articular máxima 20 rad/s, penetración máxima 20 mm, exceso articular blando máximo 0.03 rad, velocidad de referencia máxima 3 rad/s y aceleración máxima 20 rad/s². Caer está permitido. Interrupción física para velocidad >40 rad/s, penetración >30 mm, exceso articular >0.10 rad o estado no finito/fuerzas externas. No se relajaron umbrales después de medir.

`success` de los reportes heredados comprueba estos criterios H2, no todos los objetivos del Hito 2.5. No acredita una caída limpia dentro de una red física ni una pelota inmóvil.

## Posición y entorno

Pelvis inicial efectiva `(4.2, 0, 0.7794213196897599)` m; orientación frontal mundial `(-1,0,0)`. Césped/estadio 7D son visuales. Los pies contactan el suelo físico original. Línea de gol X=5, postes Y=±1.5, travesaño Z=1.8.

Los postes y la red del MJCF original tienen `contype=conaffinity=0`: no se activaron colisiones. La caja de red visual está en X=5.08. Existe además un **cajón dinámico original de 1000 kg**, centro `(5.5,0,1)`, semitamaños `(0.3,5,1)`, con colisiones habilitadas: su frente está en X=5.2. Procedencia: `g1_description/g1_liao.xml`, cuerpo `box`, geom `box_geom`; máscaras del arco en `g1_description/scene_with_ball.xml`. Ninguno fue modificado.

| Original | Pelvis final XYZ (m) | Caja envolvente de colisión final X (m) | Solapamiento máximo red visual | Entradas de contacto con cajón |
|---|---|---|---|---|
| LEFT | (4.8803, +0.5789, 0.0683) | [4.1995, 5.2529] | 91.7 mm | 592 |
| RIGHT | (4.8788, -0.5160, 0.0682) | [4.1807, 5.2503] | 97.7 mm | 613 |

Son entradas por paso/contacto, no impactos independientes. Primer contacto con cajón: LEFT t=4.618 s; RIGHT t=4.600 s. La pelvis termina delante de la línea y entre postes; parte del cuerpo cruza la línea posterior. La envolvente lateral permanece entre postes. El solapamiento con la red no es penetración del solver: la red carece de colisión. La caída no queda limpiamente contenida en un arco físico realista.

## Comparación temporal

Todos los tiempos de esta tabla se cuentan **desde la transferencia t=2 s**, no desde el inicio del proceso. Umbrales interpolados entre muestras de 500 Hz. Inicio físico: desplazamiento firmado ≥5 mm y velocidad firmada ≥0.02 m/s durante al menos cinco muestras.

| Secuencia / lado | Inicio (s) | 20 cm (s) | 40 cm (s) | 60 cm (s) | Máx. pelvis (m) | Máx. muñeca (m) | Pico articular (rad/s) | Criterios H2 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Original LEFT | 1.428 | 2.022 | 2.357 | 2.569 | 0.639 | 0.912 | 16.11 | Cumple |
| Original RIGHT | 1.420 | 2.124 | 2.473 | No alcanza | 0.514 | 0.804 | 10.74 | Cumple |
| Comprimida v1 LEFT | 0.794 | 1.344 | 1.645 | 1.821 | 0.901 | 1.064 | 36.77 | Rechazada |
| Moderada v2 LEFT | 0.912 | 1.485 | 1.795 | 1.974 | 0.884 | 1.059 | 35.14 | Rechazada |
| Moderada v2 RIGHT | 0.904 | 1.564 | 1.881 | 2.063 | 0.860 | 1.036 | 31.07 | Rechazada |
| v2 + codo de finalización LEFT | 0.912 | 1.485 | 1.795 | 1.975 | 0.870 | 1.059 | 26.56 | Rechazada |

Original: espera constante 0.2 s, preparación 0.8 s, inicio físico unos 0.42 s después de comenzar la referencia de impulso. No es una latencia IPC de dos segundos: no hay inferencia después de la transferencia. La primera referencia coincide exactamente con la última de la política. El desplazamiento crece principalmente durante la pérdida de apoyo y caída, no como una traslación rápida estabilizada.

La v1 elimina la espera y comprime preparación/impulso/extensión a 0.4/0.45/0.40 s. V2 usa 0.5/0.5/0.5 s. La finalización de ambas dura 1 s. Se mantuvieron ganancias y amplitudes originales; solamente la última prueba cambia la referencia final del codo seleccionado a 1 rad para reducir el impacto. Esto reduce el pico, pero no lo suficiente. V2 reduce el tiempo a 20 cm un 26.6% LEFT y 26.4% RIGHT, **sin superar los criterios físicos**, por lo que no se promueve.

Los picos de las comprimidas se concentran en el codo del lado de caída (v1 LEFT t=4.000 s; v2 LEFT 4.144 s; v2 RIGHT 4.216 s). Antes de t=3.8 s, el máximo era aproximadamente 5.38 rad/s: la velocidad excesiva aparece durante la caída/contacto, no por haber elevado ganancias. No se afirma una atribución causal aislada sin otro experimento.

Una inicialización adicional v1 RIGHT falló antes de integrar por `Error opening file 'meshes/right_wrist_pitch_link.STL'`. El recurso existía y estaba verificado; la causa exacta de ese fallo de carga no quedó establecida. Ensayos secuenciales posteriores y ambos visores cargaron correctamente. No se cuenta como ensayo físico ni se ocultó modificando assets.

## Velocidades, seguimiento y contribuciones reales

| Original | Pico velocidad lateral pelvis / muñeca (m/s) | Caída máxima de pelvis durante preparación | Mayor saturación continua | Penetración física máx. | Exceso articular máx. |
|---|---|---|---|---|---|
| LEFT | 1.022 / 1.383 | 20.6 mm | 42 ms | 10.55 mm | 0.01502 rad |
| RIGHT | 0.806 / 1.439 | 20.6 mm | 116 ms | 8.96 mm | 0.01443 rad |

Las secuencias rechazadas presentan penetraciones máximas 10.1–14.3 mm y saturaciones continuas máximas 132–178 ms; se respetan caps de torque, pero alcanzarlos no garantiza una caída aceptable. No hubo NaN ni advertencias numéricas en los ocho ensayos completos, incluyendo dos con visor.

Descomposición exacta del desplazamiento de muñeca en el instante de su máximo:

- LEFT: 0.912 m = 0.638 m pelvis + 0.133 m hombro respecto de pelvis + 0.141 m muñeca respecto de hombro.
- RIGHT: 0.804 m = 0.511 m pelvis + 0.142 m hombro respecto de pelvis + 0.151 m muñeca respecto de hombro.

Es una descomposición geométrica a un mismo instante, no porcentajes causales de actuación. Hay movimiento articular real: excursiones máximas piernas/torso/brazos LEFT 0.702/0.376/1.275 rad; RIGHT 0.758/0.429/1.411 rad. Trabajo absoluto integrado de actuadores por grupos LEFT 61.0/31.9/41.3 J y RIGHT 64.1/55.3/48.4 J. Incluye absorción de energía al caer. No demuestra que cada grupo aislado produzca esa fracción del desplazamiento.

## Comparación con tiros existentes

Calibraciones nominales históricas 8C, no nuevos tiros ejecutados aquí. Tiempo desde contacto pie-pelota hasta X=4.2, interpolado sobre traza de 50 Hz:

| Tiro | Tiempo (s) |
|---|---:|
| center | 0.768 |
| left_near_b060 | 0.939 |
| right_inter_m080 | 0.836 |
| right_open_m100 | 0.772 |
| right_corner_m140 | 0.792 |

La original necesita más de 2 s para 20 cm. Incluso la v1 rechazada necesita 1.344 s. Estos tiempos no justifican aptitud de atajada reactiva tras detectar el impacto. La inferencia de un agente real reduciría el tiempo disponible; no se implementó anticipación ni selección autónoma.

## Aislamiento incompleto de pelota

No se solicitó FreeKick, pero FIXEDPOSE no sostuvo al delantero: se observa su caída en capturas. La pelota presenta desplazamiento horizontal máximo por eje de 1.170 m y velocidad máxima 2.902 m/s, idénticos en todos los ensayos. No se registró contacto pie-pelota ni pelota-arquero. No se determinó el mecanismo exacto del movimiento incidental. Por tanto, no se declara cumplida una condición estricta de pelota inmóvil, ni se interpreta ese movimiento como tiro válido.

## Visor, reproducibilidad y regresiones

- Original LEFT y RIGHT: headless y visor con capturas, 3000 pasos cada uno. Igualdad **bit a bit** de `frames`, `world`, `policy` y `ball` en ambos pares.
- Totales reales observados headless original: 21.319 s LEFT y 21.318 s RIGHT; bucle 4.265/4.282 s. Con visor y once capturas: totales 31.901/34.003 s, bucle 15.436/16.562 s. Incluyen carga, inferencia auxiliar, diagnóstico y capturas; no son FPS ni costo puro de renderizado.
- Capturas reales en `validation/keeper_center_h25/original_left_viewer_02` y `original_right_viewer_02`: equilibrio, transferencia, preparación, impulso, extensión y final. Se inspeccionó el render de la extensión, que confirma raíz libre, caída y entorno del arco; no equivale a aprobación visual del usuario.
- 20 tests de H25/H2/H1 aprobados. 176 tests del paquete y núcleo aprobados. Sintaxis PowerShell comprobada por parser. Sin nuevas dependencias.
- 258 archivos previos protegidos conservan sus SHA-256, incluidos H1/H2 y fases estables. Integridad de 104 recursos verificada antes de cada ensayo. No se repitió una tanda estable completa en esta tarea; los tests y hashes no sustituyen esa prueba física.
- Salidas: `final_comparison.json`, `final_comparison.csv`, diagnósticos por ensayo, trazas completas, contactos y capturas bajo `validation/keeper_center_h25/`. Las versiones anteriores y resultados rechazados se conservan.

## Recomendación

Conservar la original como demostración manual centrada; **no adoptar ninguna rápida**. Antes de otra optimización se necesita resolver explícitamente el protocolo sin tiro/estabilidad del delantero y decidir cómo tratar el cajón posterior y la red visual, sin cambios silenciosos en la física. La maniobra actual produce una caída, no un impulso lateral suficientemente rápido para estos penales. Cualquier futura modificación debe aprobarse por separado. Hito 3 no implementado.
