# Hito 1 — Resultados del 31/10/2026

**APROBADO para composición libre, espera y ejecución de un penal.** No hay
maniobra de atajada ni integración en modos públicos. La evaluación personal del
usuario sigue pendiente; el visor y sus capturas sí fueron ejecutados técnicamente.

## Pruebas físicas realmente ejecutadas

Todas usan right_inter_m080 de 8C, bias -0.80, pelota (-1,0,0.115), delantero
(-2,0,0.793), línea de gol X=5 y paso 0.002 s, sin cambiar pesos o parámetros.

| Corrida | Posición inicial del arquero | Pasos | Resultado | Loop real s | Total proceso s |
|---|---|---:|---|---:|---:|
| baseline_01 | Sin arquero | 7000 | GOAL | 4.48 | Ver reporte |
| aside_01 | X=4.2, Y=4 | 7000 | GOAL | 10.56 | Ver reporte |
| aside_02 | X=4.2, Y=4 | 7000 | GOAL | 10.02 | 24.36 |
| viewer_center_01 | X=4.2, Y=0; visor + capturas | 7000 | GOAL | 17.76 | 37.25 |
| center_headless_01 | X=4.2, Y=0 | 7000 | GOAL | 10.04 | 24.84 |

Son 14 s simulados por corrida. El total incluye carga de políticas, RPC y,
cuando corresponde, apertura/cierre de visor, pausas y capturas. No se aisló una
medición de inicialización ni del costo puro de GPU/renderizado. No son FPS.
El visor realizó 470 sincronizaciones y cerró correctamente. En esta muestra
el bucle gráfico fue más lento que tiempo real.

## Equilibrio medido

Arquero apartado: inclinación máxima 1.901674°, deriva horizontal máxima
0.030247 m, pelvis mínima 0.767476 m. Antes del contacto pie-pelota: pelvis
mínima 0.768460 m, deriva máxima 0.027921 m e inclinación máxima 1.901674°.
En el centro se obtienen prácticamente los mismos límites; se conservan las
cifras completas y sus pequeñas diferencias en los reportes originales.

Sin caídas, NaN, avisos de MuJoCo, contactos indebidos ni saturaciones persistentes.
Sin fuerzas externas ni cambios de qpos de pelvis durante la integración.
Sin violaciones articulares. Penetración máxima del arquero: 1.939 mm.
Seis recortes iniciales de referencia, heredados y registrados como en 4B.1.
Normalizador sin cambios y reinicio recurrente cero comprobados.

Hay 29 motores del delantero y 29 del arquero, sin slider. Se verificaron raíz
libre, orden y separación de índices, contactos, masas, inercias, parámetros
articulares y actuadores. Las comprobaciones adicionales del prefijo físico
original se añadieron después de las primeras corridas, se probaron en composición
real y no cambian ningún parámetro físico. Las primeras composition.json no
contienen aún esos campos adicionales; no se reescribieron resultados anteriores.

## Validez del tiro y diferencias numéricas

Contacto físico pie-pelota: estado muestreado t=4.180 s; estado de solver
correspondiente t=4.178 s. Cruce del centro por X=5: t interpolado≈5.205625 s,
Y=-0.746025171942 m y Z=0.115019073814 m. Gol según la regla existente del centro.
No se contabilizaron atajadas ni se aplicaron fuerzas artificiales a la pelota.

Las 699 observaciones históricas posteriores a t=0 de posición Y/X/Z y velocidad
de pelota a 50 Hz de la calibración 8C coinciden EXACTAMENTE con aside_02.
La repetición aside_01/aside_02 coincide exactamente en todas las matrices de
trace.npz: arquero, decisiones, pelota, delantero y estabilidad.
La corrida centro con visor/capturas y la headless centro también coinciden
exactamente en todas esas matrices. La presentación no alteró esos registros.

Comparar un mundo SIN arquero con el que contiene el G1 libre apartado NO arroja
igualdad bit a bit. Diferencias máximas sobre los registros de los 7000 pasos:

| Magnitud | Máxima diferencia absoluta |
|---|---:|
| Posición de pelota | 6.055e-9 m |
| Velocidad de pelota | 4.436e-9 m/s |
| Posición articular del delantero | 1.913e-7 rad |
| Torque del delantero | 5.162e-5 Nm |

Se informan sin ocultarlas ni introducir tolerancias para declarar igualdad.
Son mundos compilados con distinto número de cuerpos/contactos; no se atribuyó
experimentalmente el origen exacto de cada diferencia numérica. Los recursos,
parámetros e inicialización del delantero/pelota se conservan, el contacto y
resultado coinciden y la trayectoria histórica observada de 8C sí es exacta.
No se afirma equivalencia universal para todos los tiros ni perturbaciones.

Penetración global máxima 17.626 mm, también presente en baseline_01 sin arquero;
no se confundió con penetración del nuevo G1 ni se alteró FreeKick para reducirla.
La inferencia auxiliar tuvo una latencia máxima observada de 13.87 ms en aside_01
y 48.35 ms en el ensayo gráfico. No altera el reloj simulado ni omite pasos.

## Evidencia visual

validation/free_keeper_stadium_h1/viewer_center_01/ contiene initial/final de las
cámaras behind, execution, overview y goal, generadas por Renderer con la misma
geometría visual 7D. Se inspeccionó final_behind.png: ambos G1, pelota, arco,
tribunas, pantalla y vallas UADE visibles. No es una imagen conceptual.
No se generó vídeo ni se afirma que el arquero intentara atajar en este hito.

## Tests y preservación

7 tests nuevos aprobados (límites efectivos, IDs independientes, composición,
suelas, cruce, protocolo y rechazo de respuestas de inferencia antiguas).
176 regresiones estables aprobadas. Parse PowerShell del lanzador: correcto.
239 archivos previos de app/ y calibraciones: mismos SHA-256 antes/después.
No se tocaron 8C, 9A, 7D, checkpoints, XML externos ni sus avisos. No se hizo
add, commit, push ni merge. Todos los resultados privados están bajo validation/.

## Límites

El equilibrio proviene de la política EXTERNA de locomoción de 4B.1, no de una
nueva política propia de atajada. El proceso auxiliar solo hace inferencia y el
principal es el único dueño de MuJoCo y del PD. Se usa la copia FreeKick importada
localmente, no se redistribuye. El script público no es instalación autónoma.

No se probó aún transferencia a otra maniobra, caída voluntaria, bloqueo lateral,
recuperación ni tanda de cinco con este arquero. Hito 2 queda pendiente de aprobación.
