# Hito 4A — Resultados de shadow mode

Fecha: 2026-11-01. Rama verificada: `feature/atajadas-arquero`.

**APROBADO para observación y recomendación nominal. No aprobado ni conectado para ejecución autónoma de maniobras.**

## Ensayos físicos y decisiones

Los cinco presets originales se ejecutaron como episodios aislados de 14 s/7000 pasos, con el G1 libre centrado y equilibrio de velocidad cero. No se ejecutó una nueva tanda pública ni se cambió el controlador. Se reutilizó H1 + instrumentación H3A y referencias H3B. La configuración de tiro no se suministra al agente.

Tabla: última predicción causal anterior al primer contacto/cruce. La elección de esa fila para resumir se hace después del episodio; las 700 observaciones y recomendaciones completas se conservan por ensayo.

| Tiro de evaluación | Detección, s simulados | Latencia desde impacto solver | Y prevista en X=4,2 | Z prevista | ETA restante | Recomendación | Resultado físico |
|---|---:|---:|---:|---:|---:|---|---|
| center | 4,180 | 6 ms | -0,109701 m | 0,115 m | 43,59 ms | MANTENER_CENTRO | SAVE, contacto con pierna/pie |
| left_near_b060 | 4,140 | 0 ms | +0,262014 m | 0,115 m | 40,12 ms | SIN_ACCION_VIABLE | GOAL, contacto sin atajada |
| right_inter_m080 | 4,180 | 2 ms | -0,681891 m | 0,115 m | 15,90 ms | SIN_ACCION_VIABLE | GOAL, sin contacto |
| right_open_m100 | 4,200 | 20 ms | -0,792583 m | 0,115 m | 14,37 ms | SIN_ACCION_VIABLE | GOAL, sin contacto |
| right_corner_m140 | 4,200 | 20 ms | -1,109211 m | 0,115 m | 13,47 ms | SIN_ACCION_VIABLE | GOAL, sin contacto |

Los laterales quedan fuera de la similitud con el único nominal central demostrado. H3C no consiguió una atajada y H2 no demostró alcance útil dentro del tiempo: ambas alternativas se evalúan pero se rechazan, sin inventar una probabilidad de éxito. Se compara explícitamente ETA con los aproximadamente 2 s de H2 para 20 cm.

En el central, la **primera** recomendación MANTENER_CENTRO aparece a t=4,580 s, con ETA=0,319600 s y Y=-0,129045 m. El contacto real sucede a 4,910 s. La predicción se sigue revisando; no se usa el contacto futuro para activar la regla. La recomendación no causa la atajada: esta sigue siendo cobertura pasiva.

El cero de latencia del centro-izquierda significa coincidencia con el timestamp solver de primer contacto registrado, no conocimiento anticipado. La detección usa únicamente movimiento físico observado a 50 Hz; el solver y los pasos de 2 ms tienen convenciones temporales distintas.

## Errores predictivos y límites

Error firmado = predicción menos referencia. Tabla tardía anterior, **no precisión inicial ni prueba de utilidad de una maniobra**:

| Tiro | Referencia válida para error | Error Y | Error Z | Error llegada |
|---|---|---:|---:|---:|
| center | Referencia histórica apartada, contrafactual | -0,000951 mm | +0,013343 mm | -0,743528 ms |
| left_near_b060 | Referencia histórica apartada, contrafactual | +0,018188 mm | +0,031224 mm | -0,631470 ms |
| right_inter_m080 | Cruce real del mismo episodio, sin contacto previo | -0,104978 mm | -0,033060 mm | -0,104972 ms |
| right_open_m100 | Cruce real del mismo episodio, sin contacto previo | -0,073066 mm | -0,013116 mm | -0,086945 ms |
| right_corner_m140 | Cruce real del mismo episodio, sin contacto previo | -0,071105 mm | +0,020475 mm | -0,076980 ms |

En central y centro-izquierda, el contacto ocurre antes de X=4,2 e impide o modifica el cruce. El error contra una trayectoria real sin interacción es **no evaluable** en esos dos episodios, no cero. Se usa una referencia apartada explícitamente diferenciada, cargada solo después para evaluación. Para los tres derechos, referencia apartada y cruce real coinciden.

**Primeras predicciones válidas, error contra referencia apartada** (no se ocultan):

| Tiro | Error Y inicial | Error llegada inicial |
|---|---:|---:|
| center | +0,334428 m | +0,020765 s |
| left_near_b060 | +1,485342 m | +1,809613 s |
| right_inter_m080 | +0,061679 m | +1,205284 s |
| right_open_m100 | -0,091685 m | -0,174999 s |
| right_corner_m140 | -0,104245 m | -0,183176 s |

La velocidad instantánea cerca del impacto todavía no describe la salida completa; después hay contacto con suelo/fricción. El predictor no modela esos cambios. En algunos instantes la altura es desconocida por posible rebote, y se rechaza MANTENER_CENTRO. La dispersión reciente de Y es descriptiva, no error garantizado ni incertidumbre probabilística. No se calibraron intervalos ni probabilidades ni se entrenó este agente.

## Ausencia de efectos físicos

En **cada uno de los cinco** ensayos finales (`*_02`):

- 7000 pasos; 700 consultas a 50 Hz; estado de integración idéntico antes/después de cada consulta.
- Igualdad bit a bit con el ensayo H3B sin agente de todos los arrays: pelota, delantero, arquero, decisiones/salidas de locomoción y estabilidad.
- Igualdad exacta de muestras de contacto/distancias/impulsos registradas, JSON de contactos pelota-arquero y, mediante verificación adicional, **todos** los contactos del registrador H1.
- Mismo resultado, mismas trayectorias y mismos reinicios iniciales; sin NaN, advertencias numéricas ni fuerzas externas. Los caps, ganancias y articulaciones permanecen idénticos.

Se preservan 242 archivos preexistentes Python/PowerShell/JSON/Markdown comprobados por SHA-256, incluidos experimentos anteriores y componentes estables. Perfil de 104 recursos y las 37 calibraciones verificadas por las pruebas de distribución y por el conductor físico. No se modificaron recursos externos, predictor histórico, políticas, controles, modelos, estadio ni modos públicos. El inventario histórico permanece intacto; estos archivos nuevos son un experimento separado, no un nuevo paquete público auditado.

El reporte heredado H1 marca el central como no válido según su antiguo criterio `feet_only` y penetración de 10 mm. Eso ya sucedía en H3A/H3B y se conserva sin cambiarlo. La validez de impacto se obtiene de `interception.json`, con el criterio preexistente H3A de 20 mm y contacto legítimo con pelota. No se relajaron criterios para aprobar este agente.

## Visor, tiempos y pruebas

`viewer_center_02`: visor nativo del mismo mundo, estadio 7D, cámara behind y overlay shadow. Completó 14 s/7000 pasos, 491 sincronizaciones; cierre confirmado y hilo de render terminado. Trazas exactas contra H3B y contra la headless. Pausas de presentación ≈3,002 s sin avance físico. Esto verifica la ejecución técnica; la evaluación visual personal del usuario queda disponible mediante el lanzador.

Tiempo real final headless por episodio, incluyendo carga/proceso auxiliar/presentación y análisis: 27,337; 27,358; 26,750; 26,485; 25,565 s. Sus bucles físicos: 13,887; 13,558; 13,528; 13,413; 12,994 s. Central con visor: total 35,679 s; bucle 17,080 s. No son una comparación controlada de coste gráfico ni FPS: incluyen inicialización, inferencia auxiliar y pausas. No se midió el render GPU.

- Suite distribución/core existente: **176 aprobados** (`tests/run_tests.py --include-core`).
- Suite experimental: **71 aprobados**, incluyendo 12 nuevos del agente y 59 de H1/H2/H25/H3A/H3B/H3C/H3D.
- Nueva prueba final aislada del agente: 12/12; sintaxis PowerShell: sin errores.
- Primera pasada física: cinco tiros exactos. Luego se enclavó RESOLVING tras contacto/cruce para evitar tratar rebotes como nuevos tiros y se repitieron los cinco: todos exactos. Es una corrección de observación, no de física.
- Un ensayo adicional con visor central: exacto. Total de esta tarea: 11 episodios completos, 77.000 pasos físicos. No hay una nueva atajada activa.

La primera invocación de tests apuntó por error a un nombre de módulo H3A inexistente; se corrigió la invocación y se ejecutó la suite real completa. No se cambió la prueba histórica para ocultar un fallo.

## Archivos y evidencia

Nuevos: `__init__.py`, `agent.py`, `run.py`, `analyze.py`, `test_agent.py`, `README.md`, `RESULTADOS.md` dentro de este módulo; `scripts/probar_agente_shadow_h4a.ps1`. **Ningún archivo anterior modificado.** No hubo Git de escritura, descargas, instalación ni copias de checkpoints.

Salidas privadas excluidas de Git: `validation/shadow_agent_h4a/`: `comparison.json/csv`, `additional_verification.json`, `protected_before.json`, logs de tests y carpetas de ensayo. Cada episodio conserva `shadow_decisions.json`, `summary.json`, trazas físicas, contacto y reportes heredados. `analyze.py` genera la comparación después del episodio, nunca alimenta al agente.

**Recomendación:** conservar el agente como instrumento explicable de observación. Antes de conectar acciones, mejorar/validar predicción temprana y disponer de una acción con alcance dinámico demostrado. No ejecutar BLOQUEO_BAJO o CAIDA_LATERAL por el simple hecho de que exista una etiqueta en el catálogo. No se avanzó a control autónomo.
