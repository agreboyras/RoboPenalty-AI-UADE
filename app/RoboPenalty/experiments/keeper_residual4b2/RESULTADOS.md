# Etapa 4B.2: resultado del experimento residual

30/10/2026, rama `feature/atajadas-arquero`.

**Resultado: seguro en los tres ensayos nominales, con flexión física medible,
pero NO APROBADO por recuperación articular insuficiente en la ventana fijada.**
No se aumentó amplitud, no se cambiaron ganancias, ventanas ni tolerancias después
de medir. No se habilitó ni ejecutó el visor de la maniobra.

## Comparación física real

Los tres ensayos completaron 5000 pasos, 500 decisiones y 10 segundos simulados.
El baseline se ejecutó de nuevo con el módulo 4B.1 sin modificar. Su hash coincide
exactamente con el histórico:

`9262984851026d428ebb4841ea5dfeb6adea49cd206b736059e201a8f9cbfcf4`

| Magnitud | 4B.1 nuevo | 4B.2, común a las tres repeticiones |
|---|---:|---:|
| Inclinación máxima absoluta roll/pitch | 1.52847° | 1.52847° |
| Deriva máxima | 0.0291815 m | 0.0298660 m |
| Altura mínima de pelvis | 0.766669 m | 0.763750 m |
| Penetración máxima pie-suelo | 0.00433167 m | 0.00433167 m |
| Velocidad articular máxima | 5.38033 rad/s | 5.38033 rad/s |
| Torque articular aplicado máximo absoluto | 27.87342 Nm | 27.87342 Nm |
| Saturaciones continuas | 0 s | 0 s |
| Contactos indebidos / interrupciones de seguridad | 0 / 0 | 0 / 0 |
| Recortes de referencia | 6 iniciales | Los mismos 6 iniciales |

El torque y velocidad máximos de 4B.1 se calcularon directamente sobre su traza.
Las cotas globales incluyen el transitorio inicial común; no significan que la
maniobra no haya cambiado fuerzas o velocidades posteriores.

Los estados hasta los 3 s son exactamente iguales al baseline. Después difieren
por el residual y la respuesta causal de la política. El normalizador no cambió,
h/c se reiniciaron a cero antes de cada ensayo y después evolucionaron normalmente.
No se inyectó el residual en las observaciones ni en la historia de acciones.
Las observaciones físicas sí cambian cuando el robot se mueve, como corresponde.

## Flexión y recuperación

Mediciones relativas al baseline en los mismos tiempos, evaluadas solo después
del episodio. Ventana de flexión: 5.5–6 s; recuperación: 9–10 s.

| Criterio fijado | Medición | Resultado |
|---|---:|---|
| Rodilla izquierda: incremento medio >=0.005 rad | +0.0346677 rad (1.9863°) | PASS |
| Rodilla derecha: incremento medio >=0.005 rad | +0.0485616 rad (2.7823°) | PASS |
| Descenso medio de pelvis >=0.5 mm | 3.5311 mm | PASS |
| Error medio absoluto de cada articulación intervenida <=0.005 rad | Rodilla izquierda: 0.00669776 rad | **FAIL** |
| Error medio absoluto de altura <=2 mm | 0.36248 mm | PASS |

Detalle de recuperación (error medio absoluto 9–10 s):

| Articulación | Error (rad) |
|---|---:|
| Cadera izquierda pitch | 0.00413742 |
| Rodilla izquierda | **0.00669776** |
| Tobillo izquierdo pitch | 0.00399743 |
| Cadera derecha pitch | 0.00216353 |
| Rodilla derecha | 0.00074858 |
| Tobillo derecho pitch | 0.00181363 |

El residual solicitado es exactamente cero desde 8 s. La rodilla izquierda
conserva diferencia respecto de la referencia: 0.009537 rad a 8 s,
0.008471 rad a 9 s y 0.004825 rad a 10 s. El último valor individual está por
debajo de 0.005 rad, pero **la media de la ventana predefinida no pasa**.
No se cambió la evaluación para aprovechar ese último instante. No se sabe si
una observación más prolongada demostraría recuperación sostenida.

La política no canceló esta flexión. Su salida de referencia original también
cambió: en la ventana de flexión, el aumento medio de referencia de rodilla fue
0.015956 rad izquierda y 0.024055 rad derecha respecto del baseline, antes de
añadir los 0.02 rad autorizados. La respuesta física no es igual al residual
solicitado: forma parte de un sistema con realimentación recurrente.

## Reproducibilidad y tiempos

| Ejecución | Tiempo del bucle real | Estado |
|---|---:|---|
| Baseline nuevo 4B.1 | 3.852456 s | PASS |
| Residual 1 | 5.687063 s | Seguro; FAIL recuperación |
| Residual 2 | 5.550204 s | Seguro; FAIL recuperación |
| Residual 3 | 5.249029 s | Seguro; FAIL recuperación |

Promedio residual: 5.495432 s. Son tiempos de ejecución con instrumentación;
excluyen carga de política y compilación. Las trazas y registros son distintos
entre los ejecutores, por lo que la diferencia no mide únicamente el costo del
residual ni permite atribuir un cambio de rendimiento a la política.

Hash idéntico de estados, velocidades, acciones, referencias y torques de los
tres ensayos residuales:

`746d99cee5d1a0e20fcf0cc3cc71fc80aca9c5a9f9db9d76323fa41effcad390`

No incluye tiempos de pared. Los contactos completos quedan registrados en JSONL.

## Pruebas y preservación

- Siete tests nuevos aprobados: amplitud exacta, rampas, límites/interrupciones,
  rechazo de equilibrio sin movimiento, exigencia de recuperación, episodio
  incompleto y bloqueo del visor si el informe headless no aprueba.
- 176 tests existentes aprobados mediante `tests/run_tests.py --include-core`.
- Sintaxis de PowerShell comprobada.
- 214 archivos previos del paquete revisados por SHA-256: ninguno cambió,
  incluidos 4B.1, fases históricas y recursos externos incluidos.
- No se copiaron checkpoints, no se instalaron dependencias y no se ejecutaron
  comandos Git de escritura. Se conservaron los cambios previos del working tree.

Datos locales: `validation/keeper_residual4b2/headless_01/`, con baseline,
tres ensayos, `report.json` y `comparison_samples.csv`. El CSV es una selección
de estados medidos; las trazas NPZ conservan todas las muestras. Los resultados
quedan excluidos de Git por las reglas existentes de `validation/`.

## Recomendación

Conservar 4B.1 como referencia aprobada. Esta variante demuestra que el residual
puede producir flexión física nominal sin perder equilibrio, pero aún no cumple
la preparación con recuperación acordada. No integrarla en los modos públicos.

Si el usuario lo autoriza, el siguiente experimento debería observar durante
más tiempo la recuperación con residual cero, con las mismas amplitudes y
ganancias. Esa prueba no convertiría retroactivamente este resultado en PASS.
Antes de pasos o impulsos siguen pendientes estabilidad perturbada, simetría,
convergencia del retorno y revisión de los contactos blandos de los pies.
