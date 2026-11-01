# Resultados Hito 3D

Fecha: 2026-11-01. **NO VIABLE para la secuencia probada en el presupuesto actual del centro-izquierda.** Descarga parcial demostrada; bloqueo lateral útil no demostrado. No se afirma que todas las estrategias de transferencia sean imposibles.

## Protocolo previo y escena

Pruebas sin pelota con un G1 libre y el suelo del Hito 1. Se compila la composición completa solo para comparar sus parámetros; no se ejecuta una simulación de delantero/pelota ni una segunda física. La escena ensayada contiene un único G1, 29 motores, nq=36/nv=35, una raíz libre y cero igualdades. Todas las comprobaciones de masas/inercias, geometrías, joints, transmisiones, opciones físicas, dt y suelo respecto de H1 resultaron verdaderas.

Duración fijada: 6 s/3000 pasos, inferencia a 50 Hz, un PD a 500 Hz, velocidad deseada cero. Se realizan dos baselines, dos transferencias nominales idénticas y una transferencia con visor. No hay resets dentro de los ensayos, anclaje de pelvis, slider, fuerzas externas ni otra política. Los XML/checkpoints y los Hitos anteriores no se modifican.

Ventana basal de medidas: 1.5<=t<2.0 s. Orden de ensayo externa t=2.0 s, no temporizador de un preset: aquí no hay tiros. Todos los tiempos siguientes se expresan desde esa orden. La comparación temporal descuenta 40 ms de detección medidos en H3C: presupuesto nominal 0.90 s y conservador 0.874 s hasta la superficie original H3B. No se atribuye esa detección a este experimento sin pelota.

## 1. Apoyos del G1 estable: medido

| Magnitud | Baseline |
|---|---:|
| Masa G1 | 35.112142 kg |
| Peso por gravedad original | 344.450 N |
| Fuerza vertical media pie izquierdo | 172.893 N |
| Fuerza vertical media pie derecho | 171.560 N |
| Fracción derecha media | 49.8065% |
| Centro de masa XYZ | (4.201648, -0.000118, 0.696040) m |
| Pelvis media XYZ | (4.225883, -0.000796, 0.768888) m |
| Centro de presión medio XY | (4.201825, -0.000235) m |
| Margen mínimo proyección CoM/polígono de contacto | 44.61 mm |

La suma de fuerzas coincide prácticamente con el peso. Velocidades máximas por eje de pelvis en la ventana basal: aproximadamente (2.12,4.03,0.35) mm/s. Ambos pies sostienen al robot, sin evidencia de descarga espontánea de la pierna derecha. El margen geométrico no es un certificado de estabilidad dinámica.

Los centros de presión laterales de cada pie son aproximadamente -0.13009 y +0.13063 m. Una distribución cuasiestática con 30% de carga derecha requeriría CoP Y≈-0.05187 m, desplazamiento ≈-51.64 mm.

## 2. Hipótesis geométrica previa al movimiento

Se reconstruyó la postura real del baseline y se calculó una aproximación jacobiana que intenta conservar ambos pies, combinando caderas roll negativas y tobillos roll positivos. El CoM estimado se desplazaría -0.515 m por radián de amplitud común. Esto sugiere unos 0.1003 rad para el cambio estático de CoP requerido. No es una predicción de fuerzas ni un controlador que imponga esa posición de pelvis; las restricciones lineales de pies no se satisfacen exactamente.

Se eligió **0.12 rad**, antes de ejecutar el primer movimiento, para intentar dejar margen al objetivo de descarga. Son referencias pequeñas (unos 6.9°), dentro de límites originales, con la misma rigidez/torque máximo. No se aumentaron después de observar el resultado.

Referencia evaluada: ambas caderas roll -0.12 rad y ambos tobillos roll +0.12 rad; rampa quíntica 0.35 s, mantenimiento hasta 1.20 s desde orden y retirada suave 0.50 s. Se conserva la política de equilibrio como base y se suma el residual antes de un único PD. El pico analítico del residual de referencia es aproximadamente 0.643 rad/s y 5.66 rad/s²; la referencia nativa de la política conserva su contrato y cadencia originales.

## 3. Transferencia y liberación: medido

| Evento | Tiempo desde orden |
|---|---:|
| Primera referencia residual no nula | 0.002 s |
| Reducción derecha >=10% con apoyo izquierdo suficiente, sostenida 40 ms | 0.444 s, análisis nativo |
| Descarga parcial según criterio completo, sostenida 40 ms | 0.474 s nativo; **0.480 s disponible en el controlador** |
| Primera pérdida transitoria de fuerza (<1 N) con separación positiva | 0.486 s |
| Liberación sostenida con margen >=2 mm y apoyo izquierdo | **0.966 s** |
| Punto de bloqueo +2 cm hacia la pelota | No alcanzado en 6 s |
| Punto de bloqueo +5 cm | No alcanzado |
| Punto de bloqueo +10 cm | No alcanzado |

Las condiciones y los filtros se fijaron antes de ejecutar. El análisis nativo a 500 Hz y la confirmación online a 50 Hz pueden diferir unos milisegundos; se muestran ambos. Para sostener 40 ms entre timestamps se emplean 21 muestras, no se cuentan solo 20 instantes separados por 38 ms.

Durante los primeros 0.2 s la carga derecha incluso sube: muestra instantánea aproximada izquierda 108 N/derecha 231 N. Posteriormente se descarga: al confirmar a 0.48 s la media de realimentación era izquierda 308.55 N/derecha 33.47 N. La reacción no sigue instantáneamente una predicción estática de CoP.

Hay breves pérdidas de contacto antes de 0.874 s; no se ocultan por el criterio de 2 mm. La separación positiva máxima de la suela derecha antes de ese plazo fue solo **0.0671 mm**. Eso no produjo avance lateral útil. La conclusión negativa tampoco depende de exigir 2 mm: el punto material nunca se acerca 2 cm a la trayectoria y se mueve mayoritariamente en sentido contrario.

El sistema alterna apoyos: a 0.8 s se levanta la pierna izquierda, mientras la derecha vuelve a cargar aproximadamente 240 N. La posterior liberación derecha a ~0.966 s ocurre durante estos pasos compensatorios, no como una fase de elevación de rodilla ordenada y validada. La rama prevista de liberación/bloqueo adicional no se ejecutó: no se cumplió la condición temprana predefinida para avanzar antes de 0.45 s. No se amplió ese plazo para forzar una progresión y no se habilita esa rama en el lanzador.

## 4. Alcance real y tiempo del penal

El punto seguido es un punto material fijo de la malla de pierna inferior que produjo el contacto H3B. Es geometría de diagnóstico; no se añade un colisionador ni se usa una imagen como evidencia de contacto.

- Máximo desplazamiento hacia +Y antes del plazo: **0.170 mm**, frente a 20 mm del primer objetivo declarado.
- A 0.874 s, el punto se había desplazado aproximadamente **36.15 mm en sentido contrario**, con posición `(4.11959,0.11384,0.13489)` m.
- El desplazamiento final es aproximadamente **-299.77 mm** en Y. No se contabiliza su magnitud como alcance hacia la pelota.
- En dirección contraria se recorren 2 cm a 0.525 s, 5 cm a 0.924 s y 10 cm a 0.976 s. Son movimientos físicos, pero no un bloqueo útil del tiro de +Y.
- El punto se mantiene aproximadamente entre Z=0.1218 y 0.1462 m tras iniciar. La altura no es el fallo principal: faltan dirección y oportunidad del movimiento.

La descarga parcial consume 0.48 s; la liberación sostenida observada a 0.966 s supera tanto 0.90 como 0.874 s, incluso sin añadir otra fase de movimiento. No hay evidencia para proponer una prueba de penal con esta secuencia. La ausencia de avance lateral útil sigue siendo decisiva aunque cambien unos milisegundos de convención temporal.

## 5. Estabilidad, fuerzas y límites

Transferencia nominal: inclinación máxima 8.715°, altura mínima de pelvis 0.74337 m, deriva horizontal máxima **0.25691 m**, velocidad máxima de pelvis 0.528 m/s. No se registra caída bajo la definición previa (altura<0.50 m o inclinación>=45°), pero sí cambios de apoyo y deriva no deseada.

La proyección de CoM llega a quedar unos 160 mm fuera del polígono instantáneo durante cambios de apoyo. No se interpreta automáticamente como caída: el robot cambia apoyo y sigue de pie. Es evidencia de que no se obtuvo una transferencia estática mantenida y preparada para bloquear.

Velocidad articular máxima 8.048 rad/s, penetración máxima 4.292 mm, exceso articular cero y saturación continua cero. Los torques reales permanecen dentro de los caps efectivos originales. Sin NaN, advertencias numéricas MuJoCo, fuerzas externas, autocolisiones/contactos indebidos ni contactos de cuerpo con suelo distintos de los pies.

Pico de fuerza vertical izquierda 1080.4 N en t=3.352 s, durante un paso compensatorio. El pico derecho de 538.4 N ocurre ya en t=0.014 s, en el asentamiento inicial común al baseline; no se atribuye a la transferencia. No se ocultan los impulsos de contacto altos aunque los torques estén limitados.

La política requiere 38 recortes de referencias brutas frente a 6 basales: tobillo roll izquierdo 11, tobillo pitch derecho 4 y tobillo roll derecho 23. Son recortes heredados de límites de referencia, no violaciones físicas de q ni aumento de caps. Indican una reacción mayor de la política; no se aumentaron límites para evitar esos recortes.

No se aisló la contribución causal de cada parte (contacto/fricción, inercia y respuesta de la política). El dato demostrado es que la combinación ensayada no controla la descarga y el avance de superficie requeridos. No se afirma que toda la respuesta sea «cancelación de la red».

## 6. Repetibilidad y visualización

Dos baselines y dos transferencias headless: trazas correspondientes idénticas bit a bit. Un ensayo de transferencia con visor nativo completó 6 s y coincidió exactamente con la transferencia headless. La comparación contempla datos geométricos de apoyo indefinidos al inicio (NaN en CoP/margen cuando los pies aún no tocan); los estados físicos qpos/qvel son finitos y se comparan estrictamente.

Se generaron seis capturas reales de MuJoCo de estados grabados. `render_transfer_lit_01/t_2.800.png` muestra el cambio compensatorio de apoyo; no representa una atajada. Solo el renderizador de esas imágenes aumenta contraste de iluminación/color de suelo. No se altera el modelo físico ensayado ni se interpola una animación externa. El visor está disponible para evaluación personal del usuario.

Los ensayos completos tienen 3000 pasos/6 s cada uno: cinco ejecuciones, **15000 pasos físicos**, sin penal. Los renders y el diagnóstico jacobiano no integran física adicional.

## 7. Pruebas y conservación

- **59 tests experimentales aprobados**: 10 nuevos H3D y 49 anteriores. Incluyen hull/margen de apoyo, rechazo de descarga por caída libre, fuerzas mínimas, referencias continuas/acotadas y negativa a avanzar con descarga tardía.
- **176 regresiones estables/distribución aprobadas**. Sintaxis PowerShell comprobada.
- Copia exacta comprobada de parámetros físicos respecto de H1, sin modificaciones de los XML. Los 104 recursos externos se verifican por SHA-256 antes de cada ensayo y no cambian durante él; checkpoint/configuración y normalizador se verifican con el cliente original.
- 87 archivos previos de experimentos y 258 archivos protegidos estables mantienen sus hashes. No se alteraron tiros, pelota, agentes históricos, ganancias, estadio, audio ni parser. No hubo descargas ni Git de escritura.

Archivos privados: `support_diagnosis.json`, `comparison.json`, fuerzas/contactos, estados, referencias/torques y capturas bajo `validation/weight_transfer_h3d/`. Código/documentación nuevos bajo `experiments/weight_transfer_h3d/` y lanzador independiente `scripts/probar_transferencia_h3d.ps1`.

## Recomendación

**No llevar esta secuencia al penal centro-izquierda.** Abandonar esta superposición concreta sobre locomoción de velocidad cero para el presupuesto actual. Mantener las referencias anteriores y, si se autoriza otro estudio, investigar control/habilidad con soporte monopodal o intención de paso nativa, capaz de coordinar apoyo y trayectoria de pie en vez de añadir más residual a la misma postura. No se ha implementado esa alternativa ni se integra 4C.

La conclusión es limitada al controlador, parámetros y condiciones nominales evaluadas. No es prueba de imposibilidad general del G1, de toda transferencia de peso o de una futura maniobra con otro control de apoyos. No se ejecutó ni se propone como validada una prueba integrada con pelota.
