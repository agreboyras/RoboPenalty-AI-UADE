# Hito 3B: matriz de cobertura pasiva

Evaluación realizada entre 2026-10-31 y 2026-11-01. Alcance: los cinco nominales existentes, 14 s/7000 pasos por ensayo completo. Sin maniobras nuevas, sin agente de intercepción, sin modificar H1/H2/H25/H3A ni los modos estables.

## Configuración

Conductor/composición H1 y registrador de contactos H3A reutilizados sin modificar. Arquero libre centrado: X=4.2, Y=0, frente -X, misma altura inicial efectiva y postura. Referencia: mismo arquero en Y=4. Política de equilibrio externa con velocidad deseada cero, mismo PD, ganancias, caps y contrato de observación. La política no recibe pelota ni preset. Las cinco acciones y sus calibraciones se leen del catálogo 8C y se verifican por SHA-256.

Cada pareja tiene condiciones idénticas de delantero y pelota; solo cambia la ubicación lateral del arquero según el protocolo. No se modifican velocidades, trayectorias, colisionadores o límites para facilitar bloqueos. Las reglas existentes de gol usan el centro de pelota al cruzar X=5 dentro del ancho/altura establecidos; se conserva el clasificador de fase 4A.

## Matriz nominal

| Preset | Bias existente | Referencia apartada | Centrado | Contactos físicos | Mínima separación entrante sin contacto |
|---|---:|---|---|---|---:|
| center | 0 | GOAL | **ATAJADA** | Pierna y pie izquierdos | No aplica: contacto |
| left_near_b060 | +0.60 | GOAL | **CONTACTO SIN ATAJADA** | Pierna inferior derecha | No aplica: contacto |
| right_inter_m080 | -0.80 | GOAL | **SIN CONTACTO**, GOAL | Ninguno | **0.397679 m** |
| right_open_m100 | -1.00 | GOAL | **SIN CONTACTO**, GOAL | Ninguno | **0.500884 m** |
| right_corner_m140 | -1.40 | GOAL | **SIN CONTACTO**, GOAL | Ninguno | **0.796665 m** |

Los tres mínimos positivos corresponden a la geometría del pie izquierdo (`gk/left_ankle_roll_link`), a tiempos solver 4.978, 4.916 y 4.916 s. Son distancias entre superficies físicas, incluyendo radio de pelota, no distancias entre centros. El mínimo global de toda la ventana coincide aquí con el mínimo de la aproximación; ambos se guardan separados para no mezclar futuros rebotes con cobertura inicial.

Los números positivos indican brecha espacial en la configuración ejecutada. **No son desplazamientos mínimos de pelvis**, consignas de control ni demostración de que una superficie pueda recorrerlos a tiempo. Una intervención modifica la postura y el instante de encuentro; no basta restar esa distancia al slider de una versión distinta.

Los diez ensayos nominales seleccionados completaron 14 s con validez física H3A. Hay además un intento de inicialización fallido conservado, descrito abajo. No hay nuevos tipos de atajada: solo el central, ya demostrado en 3A.

Se ejecutaron además tres repeticiones nuevas del central dentro de H3B (`repeat_center_01` a `03`): **3/3 ATAJADA**, con igualdad bit a bit de `keeper`, `decisions`, `ball`, `shooter` y `stability` respecto del primer central H3B. Esto confirma la única atajada de la matriz con la instrumentación actual. No demuestra robustez fuera de las condiciones nominales.

## Contactos y trayectorias

| Centrado | Primer contacto solver | Cuerpo | Muestras de contacto | Fuerza normal pico | Impulso sobre pelota estimado XYZ |
|---|---:|---|---:|---:|---|
| center | 4.910 s | `left_knee_link`, también `left_ankle_roll_link` | 8 | 564.96 N | (-2.70042, +0.31876, -1.15469) N·s |
| left_near_b060 | 5.054 s | `right_knee_link` | 5 | 134.39 N | (-0.73043, +0.49787, -0.11836) N·s |

Las muestras son pares de contacto por paso, no impactos independientes. Los cuerpos `knee_link` incluyen el colisionador de la pierna inferior, no solo la rodilla anatómica. Impulso estimado como suma fuerza×dt; no incluye todas las fuerzas del suelo/gravedad que actúan sobre la pelota.

**Central:** idéntico a H3A. Velocidad antes del primer contacto `(5.18624,-0.03094,0.00323)` m/s; después de ese paso `(2.75392,+0.17139,0.00693)`. Posteriormente invierte Vx a aproximadamente -1.400 m/s. No alcanza X4.2: máximo X≈4.031944 m. No hay gol durante toda la ventana.

**Centro-izquierda:** primer punto de contacto `(4.13757,+0.15650,0.13290)` m. Antes: `(3.93568,+0.02402,+0.00560)` m/s. Tras la secuencia de contacto, a 5.064 s: `(2.13479,+1.21363,-0.01957)` m/s. El balón se frena y desvía a +Y, pero conserva Vx positiva y entra:

- Sin arquero en la trayectoria: gol en t=5.305743 s, Y=+0.266761 m.
- Con arquero centrado: gol en t=5.553474 s, Y=+0.716508 m, Z≈0.115060 m.
- El contacto retrasa la llegada y desplaza lateralmente el tiro, pero no evita el gol. No se contabiliza como atajada.

**Tres derechos:** no hay contactos pelota-arquero en los 14 s. El gol se registra respectivamente a 5.205625, 5.124175 y 5.149182 s, con Y=-0.746025, -0.880578 y -1.243805 m. Pelota y delantero coinciden bit a bit entre referencia y centrado hasta el gol. Para los dos tiros con contacto, coinciden exactamente hasta el primer contacto; después la divergencia de velocidad del primer paso es 2.43316 m/s central y 0.74151 m/s centro-izquierda.

Los tiempos de impacto del delantero en convención solver son 4.174, 4.140, 4.178, 4.180 y 4.180 s. El registro posterior al paso es 2 ms más tarde. No confundir estas convenciones al comparar con calibraciones antiguas.

## Primer candidato a intervención activa

**`left_near_b060`, centro-izquierda**, es el primer nominal que no queda bloqueado. Ya existe contacto con una superficie baja y el tiempo desde impacto del delantero hasta ese contacto es aproximadamente 0.914 s. Mejorar ese encuentro es una hipótesis más acotada que intentar trasladar el cuerpo unos 40 cm hasta el intermedio derecho.

En este caso la separación faltante para obtener contacto es **cero**: la pierna ya toca la pelota, con penetración máxima de 3.086 mm. Eso no establece cuánto movimiento adicional hace falta para atajar. La incógnita es lograr un encuentro más eficaz, no cerrar una brecha vacía. No hay una amplitud mínima de movimiento para una atajada demostrada a partir de un único choque rasante.

Como diagnóstico físico, masa de pelota 0.41 kg y Vx previa 3.93568 m/s implican momento longitudinal ≈1.614 N·s. El impulso longitudinal registrado de contacto es ≈-0.730 N·s. Una estimación instantánea que ignore otras fuerzas necesitaría ≈-1.614 N·s para detener Vx; es una comparación de momento, **no una consigna de torque ni prueba de maniobra viable**. El dato observado es que queda Vx positiva y el balón entra. No se recomienda aumentar ganancias o fuerza para compensarlo.

Si se busca después el primer tiro que requiere **crear un contacto inexistente**, sería `right_inter_m080`, con brecha nominal mínima ≈0.398 m a una superficie del pie. Ese es un problema más exigente que el centro-izquierda y no se demostró alcanzable dinámicamente. No se implementó ninguna de las dos estrategias.

## Estabilidad y criterios

Todos los nominales seleccionados cumplen el protocolo de impacto H3A preexistente:

- G1 de pie: inclinación máxima 1.902°; deriva entre 3.025 y 3.439 cm; altura mínima de pelvis >=0.76740 m.
- Velocidad articular máxima 5.38033 rad/s; exceso articular 0; saturación continua 0 s; torques dentro de caps efectivos.
- Penetración máxima del arquero: 14.586 mm central, 3.086 mm centro-izquierda, 1.939 mm por pies/suelo en los tres derechos. Límite de impacto declarado: 20 mm.
- Sin NaN, advertencias numéricas MuJoCo, caídas, fuerzas externas o contactos inesperados del arquero. Se conservaron los seis recortes iniciales de referencias ya presentes en H1.
- El reporte legado H1 conserva su criterio de 10 mm y `feet_only`; puede declarar fallo ante contacto legítimo con pelota. No fue modificado ni se oculta: la validez de impacto está en `interception.json`, con los mismos criterios de 3A.

## Inicialización y limitaciones

El primer `center_right_corner_m140` falló con cero pasos por `Error opening file 'meshes/left_rubber_hand.STL'`. El recurso existía; las comprobaciones de recursos no detectaron un hash distinto. La causa de apertura intermitente no quedó determinada. No se alteró ni sustituyó el mesh. La nueva salida `center_right_corner_m140_retry01` cargó y completó los 7000 pasos con SIN CONTACTO/GOAL. Se conserva el intento inicial como RESULTADO NO CONCLUYENTE y se selecciona explícitamente el reintento en el análisis, sin sobrescribir archivos ni ocultar fallos físicos.

La sesión se interrumpió entre fechas; una referencia registra más de tres horas de tiempo real transcurrido, pero solo 14 s y 7000 pasos simulados. No se usa ese tiempo como benchmark de rendimiento. La consola conserva el aviso de migración de Hydra del recurso externo, sin cambios para silenciarlo.

El primer intento de visor con capturas (`viewer_left_near_b060`) también se detuvo con cero pasos por timeout de la primera inferencia de locomoción. Se guardaron únicamente las cuatro vistas iniciales, no imágenes del contacto. No se aumentó el timeout ni se modificó el cliente H1. El reintento sin capturas (`viewer_left_near_b060_retry01`) abrió el visor y completó 14 s/7000 pasos: CONTACTO SIN ATAJADA, GOAL, con las cinco trazas iguales bit a bit a la headless. Esto prueba ejecución técnica del visor, no sustituye la observación personal del usuario. No se afirma una causa demostrada del timeout ni se garantiza que no vuelva a ocurrir.

Esta matriz no prueba robustez a perturbaciones, variaciones de tiro o cambios de postura. Los cuatro laterales tienen una pareja nominal por acción. No se presentan cinco casos elegidos como probabilidad de atajada. «Pasivo» no significa articulaciones sin torque: el equilibrio neuronal/PD permanece activo, pero no hay percepción de balón ni decisión de atajada.

## Evidencia y conservación

`coverage.json`, `coverage.csv` y `coverage.log` en `validation/passive_coverage_h3b/` contienen pares, distancias, fuerzas, estados y comparación exacta. Cada carpeta conserva `report.json` original, `interception.json`, contactos y trazas completas.

31 archivos fuente/documentación de H1/H2/H25/H3A y 258 archivos previos protegidos conservan sus SHA-256. El central de H3B reproduce bit a bit los cinco arrays de la traza H3A. Los recursos externos se verificaron por 104 SHA-256 antes de cada ensayo y sin cambios durante las ejecuciones. No se modificaron calibraciones, políticas, ganancias, colisionadores, estadio ni modos públicos. No hubo Git de escritura ni descargas.

Tests ejecutados: 10 de categorías/referencias H3B + 29 de H3A/H1/H2/H25 = **39 aprobados**; suite estable/distribución: **176 aprobados**. Sintaxis PowerShell comprobada. Las pruebas físicas, no estos tests, respaldan la matriz.

**Estado final:** caracterización pasiva nominal completada, sin intervención activa implementada. Catorce ensayos completos (diez nominales, tres repeticiones centrales y un visor) y dos intentos de cero pasos conservados como no concluyentes. Los fallos intermitentes de carga/inferencia siguen siendo una limitación operativa. No se avanzó a otra etapa.
