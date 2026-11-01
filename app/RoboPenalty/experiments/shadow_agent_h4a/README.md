# Hito 4A: agente inteligente en modo observación

Experimento independiente. No integra nuevas maniobras en los modos públicos y no cambia el equilibrio, las referencias articulares ni el PD. `SIN_ACCION_VIABLE` significa ausencia de intervención demostrada: **no desactiva el equilibrio**.

## Arquitectura y límites de información

Percepción física a 50 Hz → predictor histórico de fase 3B → evaluación de evidencia/tiempo/riesgo → recomendación → registro.

`agent.py` recibe solamente una dataclass inmutable: tiempo, posición/velocidad mundial de pelota, posición/cuaternión mundial del arquero y fase física observada. No recibe MuJoCo, preset, bias, etiqueta de resultado, calibración ni trayectoria futura. Los arrays de MuJoCo se copian a tuplas; el estado de integración se compara antes/después de cada consulta.

`run.py` reutiliza un conductor H1 aislado y el registrador H3A. La selección externa del tiro es exclusivamente configuración de evaluación, como en H3B. La política de locomoción cero y el único PD siguen funcionando exactamente igual. Las recomendaciones no tienen ningún camino de ejecución de maniobras.

La fase observada es PREPARING hasta detectar movimiento hacia el arco; SHOOTING durante aproximación; RESOLVING queda enclavada tras contacto conocido, cruce del plano o cese del avance. Son estados causales de observación; no se afirma incorporar el orquestador público 9A. READY/FINISHED se muestran en la presentación del ensayo. Los rebotes no reinician un penal.

La detección exige Vx > 0,5 m/s antes de X=4,2. Es un umbral de ingeniería para movimiento entrante, no prueba por sí sola de contacto pie–pelota; el registrador independiente comprueba el contacto real y permite medir la latencia después del episodio.

## Predicción

Se importa **sin modificar** `phase3b/predictor.py`. Plano X=4,2; velocidad horizontal instantánea constante; altura rasante o balística según el predictor. Se suministran campos matemáticos neutros para su antigua conversión de coordenadas del rail; se descarta `rail_target_m`. No hay slider en este modelo.

El horizonte máximo heredado es 3 s. El predictor no estima frenado por fricción, contactos con robots ni rebotes futuros. Si anticipa contacto con el suelo, la altura puede ser desconocida: no se inventa una altura de intercepción. Se informa el rango de Y prevista de las últimas diez observaciones como dispersión descriptiva, **no como intervalo de confianza o probabilidad aprendida**.

## Catálogo y reglas explícitas

| Acción | Evidencia | Elegibilidad |
|---|---|---|
| MANTENER_CENTRO | Atajada central nominal H3A/H3B repetida | Predicción y pose similares al caso demostrado; no requiere nuevo movimiento |
| BLOQUEO_BAJO | H3C movió articulaciones y empeoró el contacto | Evaluada y rechazada: no hay atajada activa útil demostrada |
| CAIDA_LATERAL | H2 necesitó aproximadamente 2 s para 20 cm | Se compara ETA con esa referencia temporal; aun con tiempo, no hay intercepción validada |
| SIN_ACCION_VIABLE | Abstención explícita | Seleccionada si falta evidencia para intervenir |

La regla es lexicográfica: primero validez de predicción/fase; después evidencia de capacidad y tiempo; luego compatibilidad con pose/caso nominal y riesgo. No hay suma de pesos ni probabilidades supuestamente aprendidas.

El ejemplar histórico central sin obstrucción tiene Y=-0,109700222 m, Z≈0,115 m en X=4,2. Para **similitud**, se permite ±0,02 m lateral/vertical, posición de pelvis dentro de ±0,05 m en X/Y de (4,2,0), inclinación <15° y orientación hacia -X. Son tolerancias explícitas de abstención, **no una región de cobertura físicamente validada**, ni garantía de SAVE. El dato histórico es calibración previa; no es futuro del episodio. Solo se demostró el nominal. Cambiar esas tolerancias exige una nueva evaluación.

## Ejecución privada en esta computadora

Desde la raíz de RoboPenalty-AI-Complete:

```powershell
.\scripts\probar_agente_shadow_h4a.ps1 -Accion center -Viewer -Camara behind
.\scripts\probar_agente_shadow_h4a.ps1 -Accion left_near_b060 -Viewer -Camara goal
.\scripts\probar_agente_shadow_h4a.ps1 -Accion right_inter_m080 -Viewer -Camara goal
.\scripts\probar_agente_shadow_h4a.ps1 -Accion right_open_m100 -Viewer -Camara goal
.\scripts\probar_agente_shadow_h4a.ps1 -Accion right_corner_m140 -Viewer -Camara goal
```

Sin `-Viewer`, ejecuta headless. Cada comando ejecuta **un penal aislado** de 14 s/7000 pasos. No es una nueva tanda pública. Overlay: fase observada, recomendación actual, Y prevista, ETA y motivo abreviado. No se debe esperar una nueva zambullida: el arquero conserva su equilibrio pasivo. La recomendación puede cambiar al mejorar las observaciones y se abstiene al terminar la aproximación.

El visor se cierra al terminar; para interrumpir, cerrar su ventana o Ctrl+C en consola. Una interrupción no es una prueba física completa. Para repetir, volver a ejecutar el comando: las salidas llevan fecha y nunca sobrescriben resultados existentes.

El lanzador reutiliza **entornos privados y referencias locales** ya presentes en `validation/`: entorno Python del ensayo de instalación, proceso Torch de 4B.1, Deploy importado del ensayo previo, checkpoint externo de locomoción y referencias H3B. No descarga ni copia esos recursos; no es un instalador portátil. Si faltan, `Resolve-Path` falla explícitamente. La CLI Python permite rutas configurables. No se añaden checkpoints al repositorio.

## Evaluación posterior e interpretación

Cada ejecución genera `shadow_decisions.json`, `summary.json`, `trace.npz`, `interception_trace.npz`, contactos y reportes físicos heredados. `summary.json` compara todos los arrays de H1, muestras geométricas y contactos exactos contra el H3B del mismo tiro. Los JSON de referencia/calibración no entran al agente.

`actual_unobstructed_errors` contiene error Y/Z/tiempo de todas las predicciones entrantes cuando el cruce de X=4,2 ocurre antes de contacto con arquero. Para central y centro-izquierda, el contacto altera o impide ese cruce: ese error se marca **no evaluable**, no cero. `counterfactual_aside_errors` usa después del episodio la referencia histórica apartada de idéntico tiro para evaluar la predicción sin interacción. Ambas evaluaciones están separadas.

La tabla comparativa usa la última observación previa al contacto/cruce, seleccionada **solo para el informe posterior**. El agente no conoce ese instante futuro. También se guarda la primera predicción: no se ocultan errores tempranos ni se usa la buena precisión tardía como prueba de tiempo suficiente para actuar.

## Defensa académica

- **Tipo:** agente basado en modelo y reglas, deliberativo y con memoria del instante de detección. No es aprendizaje automático del arquero de decisión.
- **Entorno:** físico, dinámico, continuo, parcialmente observable a 50 Hz; contactos y evolución futura no conocidos; ejecución determinista bajo condiciones idénticas comprobadas.
- **Sensores:** posiciones/velocidades físicas y pose propia; fase causal. Se utiliza estado perfecto del simulador, sin ruido ni visión por cámara: esa es una limitación.
- **Acciones:** recomendaciones simbólicas; el efector está desconectado en shadow mode.
- **Objetivo:** elegir una respuesta con evidencia suficiente y explicar por qué abstenerse. No maximizar artificialmente el número de atajadas.
- **Evaluación:** causalidad, error predictivo por horizonte, justificación de reglas, abstención y ausencia exacta de efectos físicos. La atajada observada sigue siendo cobertura pasiva, no eficacia causal del nuevo agente.
- **Conceptos de IA:** percepción, representación de estado, modelo predictivo, base de conocimiento, reglas de decisión, selección de acciones, racionalidad limitada por capacidades e incertidumbre, separación entre simulación y agente.

No se afirma aprendizaje, generalización, nuevas atajadas ni ejecución autónoma. Esa integración necesita autorización y un catálogo con capacidades físicas verificadas.
