# Resultados Hito 3C

Fecha: 2026-11-01. **BLOQUEADO para demostrar una atajada activa útil.** La infraestructura funciona; el residual pequeño empeora el bloqueo. No hay una incompatibilidad de instalación que explique el resultado. Se detiene la calibración sin probar 0.08 rad, cambiar ganancias o diseñar otro movimiento.

## Diagnóstico previo del contacto H3B

Primer contacto centro-izquierda: solver t=5.054 s, punto `(4.137575,0.156504,0.132896)` m, geom `gk/geom_025`, mesh/cuerpo `gk/right_knee_link`, superficie lateral baja de pierna inferior. Fuerza normal pico inicial 134.3916 N; fuerza mundial original sobre pelota `(-121.02896,+93.90746,-25.50253)` N. No confundir fuerza con normal geométrica: incluye fricción.

Reconstrucción cinemática con posturas reales: normal sobre pelota aproximadamente `(-0.36545,+0.91753,-0.15680)`, predominantemente lateral. Es una normal geométrica reconstruida, no una nueva fuerza simulada. Velocidad previa `(3.93568,+0.02402,+0.00560)` m/s; después del primer paso `(3.34040,+0.47294,+0.03100)`. Tras los cinco contactos conserva Vx≈2.13479 m/s y entra en el arco por Y=+0.71651 m.

Al instante previo al contacto, la cadera roll derecha estaba en -0.02445 rad con velocidad -0.00362 rad/s; el tobillo roll derecho en +0.03235 rad con velocidad +0.00380 rad/s. Rodilla derecha ≈0.51235 rad. El robot estaba equilibrado y casi inmóvil; la evidencia no señala una maniobra activa previa.

La derivada geométrica del punto respecto de cadera roll derecha, con raíz fija, era aproximadamente `(-0.00992,-0.48719,-0.04071)` m/rad. Por eso -0.04 rad sugería +19.5 mm hacia +Y con esa hipótesis. **Era una estimación de geometría con raíz fija, no alcance dinámico demostrado.** La compensación opuesta de tobillo buscaba moderar la rotación del pie. No se alteraron colisionadores para cambiar la normal.

## Ensayo y activación causal

Escenario configurado externamente como `left_near_b060`, con parámetros del catálogo intactos. El controlador no recibe ese identificador. Utiliza dos observaciones físicas y proyección horizontal instantánea. Primera evidencia útil t=4.160 s; detección confirmada t=4.180 s. Impacto del delantero en convención solver t=4.140 s: latencia de detección 40 ms.

Primer residual no nulo en referencia a t=4.182 s: 2 ms después de detectar. La respuesta real de cadera se distingue de la pasiva a t=4.316 s, 136 ms después de detectar, definiendo descriptivamente respuesta como diferencia >=0.001 rad durante cinco muestras seguidas. Esta definición es una medida de latencia, no un umbral de éxito cambiado tras ejecutar.

Solo se añadieron cadera roll derecha -0.04 y tobillo roll derecho +0.04 rad, rampas de 0.30 s y recuperación de referencia 0.35 s. La retirada empieza a t=5.200 s por observación de pelota más allá de X4.4; termina a 5.550 s. El residual final es cero. La política y el PD continúan activos normalmente. No se exige que la postura final coincida exactamente con la pasiva.

## Comparación física durante 14 segundos completos

| Ensayo | Resultado | Primer contacto arquero | Fuerza normal pico | Impulso contacto X | Y al ingresar en X5 |
|---|---|---:|---:|---:|---:|
| C: referencia apartada nueva | GOAL | Ninguno | 0 N | 0 | +0.266761 m |
| A: pasivo centrado nuevo | CONTACTO SIN ATAJADA, GOAL | 5.054 s | 134.39 N | -0.73043 N·s | +0.716508 m |
| B: activo 0.04, ensayo 1 | CONTACTO SIN ATAJADA, GOAL | 5.056 s | 117.41 N | -0.67479 N·s | +0.664688 m |
| B: misma maniobra, repetición | Mismo resultado | 5.056 s | 117.41 N | -0.67479 N·s | +0.664688 m |
| B: visor en vivo | Mismo resultado | 5.056 s | 117.41 N | -0.67479 N·s | +0.664688 m |

Los nominales activos y el visor coinciden bit a bit en las cinco trazas H1. La referencia apartada nueva y la pasiva nueva coinciden bit a bit con sus homólogas H3B. Antes del primer contacto, el delantero y la pelota activos coinciden exactamente con la referencia libre: no se cambia el tiro para obtener el resultado.

La fuerza pico cae aproximadamente 12.6% y la magnitud de impulso longitudinal de contacto cae aproximadamente 7.6%. El gol activo ocurre a 5.516881 s, frente a 5.553474 s pasivo: se retarda menos y queda más cerca del centro del arco. No se considera mejora que cambie la referencia o se observe movimiento.

Impulso activo completo estimado: `(-0.67479,+0.46779,-0.06651)` N·s. Antes del contacto activo Vx≈3.92992 m/s; después del primer paso Vx≈3.38095 m/s. La pelota sigue hacia el gol. Los impulsos son suma fuerza×dt de los contactos G1, no el impulso neto de todas las fuerzas, incluido el suelo.

No se ejecutaron tres repeticiones adicionales de una atajada porque **no se consiguió ninguna atajada activa**. Se confirmó dos veces el mismo fallo nominal y una vez con visor, sin reajuste.

## Movimiento real: por qué falla la hipótesis inicial

Comparando con la pasiva al mismo tiempo de contacto:

- Cadera roll derecha real cambia aproximadamente **-0.05133 rad** y tobillo roll **+0.03402 rad**. Hay actuación física, no solo referencias distintas.
- La pelvis se desplaza aproximadamente **-20.67 mm en Y** respecto de la pasiva, en dirección opuesta a la pelota centro-izquierda.
- El origen de rodilla/pierna inferior se desplaza aproximadamente **-10.19 mm en Y**. No son 10 mm de desplazamiento del punto material de choque.
- El origen del tobillo cambia solo **+0.071 mm en Y**: permanece prácticamente en su apoyo físico.
- Reconstruyendo el mismo punto material de la malla que produjo el contacto pasivo, a t=5.054 s pasa de Y=0.156504 a Y=0.153684 m: **retrocede 2.820 mm**, en vez de acercarse a la pelota. Esa comparación es cinemática posterior, no una animación ni un punto artificial usado por el controlador.

Los datos son compatibles con una cadena apoyada en el suelo: el giro de cadera no desplaza libremente el pie y induce movimiento compensatorio del cuerpo. No se aisló experimentalmente cuánto corresponde a fricción, geometría de apoyo o reacción de la política de equilibrio; no se atribuye todo a que la red «cancele» el residual. La articulación sí se movió; faltó desplazamiento útil de la superficie de intercepción.

## Seguridad y control central

La maniobra activa completa es físicamente válida según criterios declarados antes de ejecutarla: inclinación máxima 1.902°, altura mínima 0.76629 m, deriva máxima 4.313 cm, velocidad articular máxima 5.38033 rad/s, exceso articular cero, penetración máxima 2.731 mm y saturación continua cero. Torques dentro de caps efectivos, sin NaN, advertencias numéricas MuJoCo, fuerzas externas o contactos inesperados. Sin caídas en estos ensayos, aunque el experimento no ancla pelvis ni prohíbe geométricamente caer.

Después de la activación el bucle no impone el límite de inclinación/altura de equilibrio H1, para no impedir una caída física permitida. Se conservan criterios de impacto de 20 mm/20 rad/s/0.03 rad y umbrales de interrupción mayores documentados en README. No se cambió el modelo para conseguir estabilidad. El único escritor de los torques del arquero sigue siendo el PD, después de sumar referencia de política y residual.

**Control central con mismos parámetros:** la condición de activación no se cumple; no hay residual. Resultado ATAJADA PASIVA, con trazas `keeper`, `decisions`, `ball`, `shooter`, `stability` exactamente iguales al central H3B. Esto conserva ese nominal; no demuestra que forzar la maniobra sobre un central funcione, ni generalización a trayectorias no evaluadas.

## Pruebas, visor y conservación

- Visor nativo abierto: completó 14 s y coincidió con headless. No se generaron capturas del movimiento en esta tarea; no se afirma evaluación visual humana del usuario. Se entregan comandos para observar el ensayo negativo.
- 10 tests nuevos H3C y 39 de H3B/H3A/H1/H2/H25: **49 aprobados**. Suite estable/distribución: **176 aprobados**. Parser PowerShell correcto.
- Se añadió validación de forma/finitud de la salida de política antes del PD, conservando exactamente el recorte de límites H1 para salidas válidas. Todas las salidas registradas tienen 29 valores finitos; esta comprobación no cambia los ensayos válidos.
- 80 archivos previos de experimentos y 258 archivos protegidos de la versión estable: SHA-256 sin cambios. Los 104 recursos externos y la calibración se verifican estrictamente antes de cada ensayo; no hubo cambios durante las ejecuciones.
- No se modificaron checkpoints, normalizador, XML, colisionadores, parámetros de pelota, tiros, ganancias, Hitos anteriores, 8C, 9A, 7D ni modos públicos. No se integró 4C, no hubo descargas ni Git de escritura.

Datos: `validation/low_block_h3c/contact_diagnosis.json`, `material_point.json`, `comparison.json`, trazas NPZ, observaciones físicas, referencias original/residual/final y contactos por ensayo. Los resultados negativos no se sobrescriben.

## Recomendación

No conservar esta maniobra como mejora de jugabilidad. Antes de otro ensayo de bloqueo bajo convendría estudiar el apoyo y la transferencia de peso/descarga del pie: la suposición de poder trasladar la superficie con un pequeño giro de cadera era incorrecta para este equilibrio con pie apoyado. Eso requiere otra autorización; no se implementó otra maniobra, mayor amplitud ni catálogo de atajadas. El resultado no descarta todas las soluciones con control propio, pero sí impide presentar este residual como atajada activa útil.
