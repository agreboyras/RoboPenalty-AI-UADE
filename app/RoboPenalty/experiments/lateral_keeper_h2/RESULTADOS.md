# Hito 2 — Resultados del 31/10/2026

**APROBADO como maniobra lateral manual de laboratorio**, con caída física y
extensión articular observables. No se aprueba como atajada, zambullida humana
optimizada ni acción suficientemente rápida para los tiros actuales. No se
integra en los modos públicos ni en el agente. Evaluación visual personal pendiente.

## Ejecuciones físicas

Primero se probó transferencia sin maniobra. transfer_01 se detuvo antes de dar
pasos por un error de serialización de matrices JSON; se corrigió solo el registro.
transfer_02 completó 3 s: referencia sin salto, política detenida desde 2 s,
inclinación máxima 1.90°, pelvis mínima 0.7687 m, sin saturación ni caída.

Luego left_01 pasó los criterios predefinidos y se ejecutó la variante simétrica
right_01. balance_01 continuó con política durante 6 s como control. Finalmente
se ejecutaron ambos visores con cinco capturas cada uno. Corridas conservadas:

| Ensayo | Pasos | Simulado s | Loop real s | Total real s | Resultado |
|---|---:|---:|---:|---:|---|
| transfer_02 | 1500 | 3 | 2.62 | 15.61 | Transferencia sin salto, de pie |
| balance_01 | 3000 | 6 | 6.95 | 24.56 | De pie |
| left_01 | 3000 | 6 | 5.04 | 19.41 | Caída lateral/diagonal válida |
| right_01 | 3000 | 6 | 6.20 | 23.96 | Caída lateral/diagonal válida |
| left_viewer_02 | 3000 | 6 | 12.35 | 28.13 | Visor y capturas, cierre correcto |
| right_viewer_02 | 3000 | 6 | 12.63 | 29.27 | Visor y capturas, cierre correcto |

Tiempos incluyen instrumentación. Los totales incluyen carga de política,
apertura/cierre, pausas y capturas cuando corresponden. No se aisló el costo de
GPU ni se obtuvieron FPS del visor. No se instalaron paquetes de vídeo.

## Movimiento real medido

La tabla usa el desplazamiento firmado hacia el lado solicitado, desde el estado
de la transferencia a los 2 s; no es solamente cambio de objetivos articulares.

| Métrica | Equilibrio | LEFT | RIGHT |
|---|---:|---:|---:|
| Pelvis: máximo hacia lado solicitado | 0.000 m | 0.639 m | 0.514 m |
| Muñeca elegida: máximo hacia lado | 0.000 m | 0.912 m | 0.804 m |
| Aumento lateral muñeca–hombro | 0.0013 m | 0.149 m | 0.154 m |
| Inclinación máxima | 1.90° | 84.99° | 85.20° |
| Pelvis mínima | 0.768 m | 0.0683 m | 0.0681 m |
| Penetración máxima del arquero | 1.94 mm | 10.55 mm | 8.96 mm |
| Exceso máximo de límite articular blando | 0 | 0.0150 rad | 0.0144 rad |
| Velocidad articular máxima real | 5.38 rad/s | 16.11 rad/s | 10.74 rad/s |
| Mayor saturación continua por motor | 0 | 44 ms | 116 ms |

El control de equilibrio tiene pequeñas derivas en sentido contrario al +Y de
la tabla; no significa que el cuerpo esté inmóvil. Desde la postura inicial t=0,
su deriva horizontal máxima es 2.87 cm y su muñeca elegida se desplaza lateralmente
hasta 1.81 cm. Para LEFT desde t=0: pelvis +0.638 m y muñeca +0.910 m; para RIGHT:
pelvis -0.516 m y muñeca -0.807 m. Datos completos: summary.json.

Preparación: la pelvis desciende 20.63 mm entre la transferencia y el final de
preparación en ambos lados. A 3 s, rodilla izquierda real 0.7367 rad frente a
0.5414 rad del control de equilibrio. Hay flexión ejecutada, no solo referencias.

La caída es DIAGONAL. El desplazamiento longitudinal final de pelvis es +0.655 m
LEFT y +0.653 m RIGHT, hacia la línea de gol. No es una zambullida paralela pura a
la línea. No se simula una recuperación: termina en el suelo manteniendo una
referencia final obtenida suavemente desde articulaciones reales.

Los contactos físicos incluyen pies y, durante la caída, cadera/pelvis y segmentos
de brazo/hombro según el lado; se guardan todos, incluidas autocolisiones activas.
Impulso total pie–suelo lateral medido: +71.46 Ns LEFT y -70.39 Ns RIGHT. No es
un impulso externo aplicado: integra fuerzas del solver sobre las geometrías de
pies. Hubo solo unas decenas de milisegundos acumulados sin contacto activo con
suelo: no se presenta como un salto sostenido.

Todos los torques reales estuvieron dentro de los límites efectivos de H1.
La saturación de cintura pitch de RIGHT duró 116 ms y debe revisarse antes de
ampliar la maniobra. Los límites articulares del modelo se conservaron; el solver
blando permitió los excesos medidos de hasta 0.015 rad. No se declaran límites
ideales exactamente satisfechos ni seguridad de hardware real. El pico de 16.11
rad/s de LEFT fue en codo derecho a 4.606 s, después de comenzar la caída.

Sin NaN, fuerzas externas, avisos físicos de MuJoCo ni reinicios durante el ensayo.
El aviso Hydra14MigrationWarning de las importaciones antiguas permanece registrado,
no es un aviso del solver ni se modificó código externo para eliminarlo.

## Tiempo y utilidad futura

LEFT supera 20 cm de desplazamiento de pelvis a t=4.024 s y RIGHT a t=4.126 s:
2.024 y 2.126 s después de la transferencia. A los 0.8 s de transferir aún está
preparándose y el desplazamiento lateral es cercano a cero. No se demuestra
alcanzabilidad dentro de la ventana de reacción de los tiros actuales.
Esta secuencia tiene amplitud útil, pero su sincronización NO está resuelta para
interceptar una pelota. No se anticipó el tiro usando información futura: este
laboratorio empieza por temporizador manual y no pretende ser una decisión causal.

## Conservación, reproducibilidad y pelota

Los primeros 2 s del mundo y las 100 inferencias de política coinciden exactamente
entre equilibrio y cada maniobra. Después no se consulta nuevamente la política.
El mismo PD escribe una sola vez por paso los motores del arquero.

LEFT headless y LEFT viewer coinciden exactamente en frames, world, policy y ball.
Lo mismo ocurre con RIGHT. Son dos ejecuciones nominales por lado, no un estudio
de robustez frente a perturbaciones. Los datos de configuración y los hashes del
código final constan en las corridas con visor. Las primeras corridas no contienen
las adiciones posteriores de metadatos/fuerzas mundiales; no se sobrescribieron.

El tiro y la pelota conservan parámetros y recursos; se usa el bias del catálogo
8C verificado, sin modificarlo. No hay contactos pelota–arquero por estar apartado.
Los registros de pelota coinciden EXACTAMENTE entre equilibrio/LEFT/RIGHT hasta
cruzar X=5 a t≈5.205625 s, Y=-0.746025 m, Z=0.115019 m. Después del gol las
trayectorias difieren hasta 20.63 mm LEFT y 0.908 mm RIGHT. No se oculta esa
diferencia ni se declara equivalencia total. Podría relacionarse con la resolución
numérica de contactos activos en el mismo mundo, pero no se identificó causalmente
su origen exacto. No se cambiaron solver, contactos ni pelota para hacerla desaparecer.

250 archivos previos, incluido todo H1 y su lanzador: SHA-256 sin cambios.
14 tests experimentales (7 H2 y 7 H1) aprobados; 176 regresiones estables aprobadas.
Sintaxis PowerShell del nuevo lanzador correcta. No hubo add, commit, push, merge,
cambios a main, descarga de dependencias ni copia de checkpoints externos.

## Evidencia y límites

Se ejecutaron ambos visores nativos y se inspeccionaron capturas reales de
preparación, impulso, extensión y caída. Están en validation/lateral_keeper_h2/
left_viewer_02 y right_viewer_02. No son animaciones ni imágenes conceptuales.
La naturalidad de la técnica todavía debe juzgarla el usuario. Se ve una caída
con extensión moderada, no una atajada futbolística validada.

No se entrenó ninguna política ni se usó goalkeeper.pt. No se modificaron H1,
8C/9A/7D, contactos, pesos o parámetros físicos. Los recursos y entornos externos
siguen siendo requisitos locales no redistribuidos. La cámara es privada del
experimento y el escenario compartido se reutiliza sin editarlo.

Antes de un Hito 3 sería necesario autorizar y estudiar sincronización causal,
reducción del desplazamiento longitudinal, trayectoria de muñecas a altura de
pelota y saturación/impacto. No se implementa ninguna de esas mejoras aquí.
