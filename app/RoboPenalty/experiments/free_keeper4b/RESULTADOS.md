# Etapa 4B: equilibrio libre nominal

Fecha: 30/10/2026. Rama: `feature/atajadas-arquero`.

**Resultado: equilibrio nominal demostrado durante 10 segundos**, con el
adaptador, inicialización y protecciones documentados. No demuestra robustez
global, capacidad de desplazamiento, salto, caída, recuperación ni atajada.

## Ejecuciones reales

| Ensayo | Pasos / decisiones | Tiempo simulado | Tiempo real del bucle | Resultado |
|---|---|---|---|---|
| Headless 1 | 5000 / 500 | 10 s | 4.380133 s | PASS |
| Headless 2 | 5000 / 500 | 10 s | 3.514680 s | PASS |
| Headless 3 | 5000 / 500 | 10 s | 3.833325 s | PASS |
| Visor nativo en vivo | 5000 / 500 | 10 s | 10.009979 s | PASS |

Los tiempos incluyen instrumentación y, en el visor, pacing de tiempo real;
excluyen carga del checkpoint, calentamiento, compilación e inicio del visor.
No son benchmarks de inferencia ni FPS del visor. Promedio headless: 3.909379 s.
El tiempo flotante acumulado de MuJoCo fue 10.000000000000009 s.

Las cuatro ejecuciones producen exactamente el mismo hash de estados completos,
decisiones y estado final:

`9262984851026d428ebb4841ea5dfeb6adea49cd206b736059e201a8f9cbfcf4`

No se incluyen tiempos de pared en este hash. No es una comparación con 8C:
la escena libre es deliberadamente diferente de la escena con guía lateral.

## Métricas físicas comunes

| Magnitud | Medición |
|---|---|
| Altura inicial de pelvis | 0.77942132 m |
| Altura mínima/final | 0.76666895 m |
| Máximo absoluto roll/pitch | 1.52847159° (criterio <15°) |
| Máxima deriva horizontal | 0.02918146 m (criterio <0.10 m) |
| Máxima velocidad lineal de base, muestras previas a paso | 0.10137694 m/s |
| Máxima velocidad angular de base, mismas muestras | 1.00621419 rad/s |
| Máxima velocidad articular absoluta | 5.38032843 rad/s |
| Máximo torque articular aplicado absoluto | 27.87341556 Nm |
| Saturación de torque continua | 0 s |
| Violaciones de posición articular | 0 pasos |
| Contactos distintos de pies-suelo | 0 pasos |
| Caídas / advertencias / estados no finitos | 0 / 0 / 0 |
| Máxima penetración de contacto pie-suelo | 0.00433167 m |
| Máximo absoluto de h/c tras cada reset | 0 |
| Cambios en buffers del normalizador | Ninguno |

La penetración es la distancia negativa informada por contactos blandos de
MuJoCo. Es significativa respecto del radio de 5 mm de las esferas de los pies;
debe revisarse antes de extrapolar a impulsos o aterrizajes. No se modificó la
geometría, rigidez de contacto o tolerancia para mejorar esta cifra.

## Protección de referencias: diferencia explícita

El checkpoint y su normalización no se modificaron. El adaptador de seguridad
recorta las referencias al rango del XML. Hubo seis recortes durante los
primeros 60 ms de cada ensayo:

| Tiempo | Articulación | Referencia cruda | Referencia limitada (rad) |
|---|---|---|---|
| 0.00 | Tobillo derecho pitch | 0.750974 | 0.523600 |
| 0.02 | Tobillo derecho pitch | 0.979596 | 0.523600 |
| 0.02 | Tobillo derecho roll | -0.351429 | -0.261800 |
| 0.04 | Tobillo derecho pitch | 0.873636 | 0.523600 |
| 0.04 | Tobillo derecho roll | -0.278282 | -0.261800 |
| 0.06 | Tobillo derecho pitch | 0.632982 | 0.523600 |

No hubo violaciones en las posiciones reales. El éxito corresponde a esta
cadena protegida; no demuestra que ejecutar las referencias crudas sin
protección produzca el mismo resultado. No se ensayó ni recomienda retirar
los límites. No hubo recorte de torque solicitado.

## Pruebas

- Siete tests del experimento: observaciones, gravedad, permutación, hashes de
  configuración, criterios de rechazo, escena libre/límites efectivos y cierre
  anticipado del visor con liberación de contexto.
- Cuatro tests con el checkpoint externo real: salida contra inferencia directa,
  fórmula del normalizador y buffers congelados, reinicio h/c y última acción,
  secuencia exactamente reproducible después del reinicio.
- `tests/run_tests.py --include-core`: suites existentes aprobadas, incluidos
  inventario, 37 calibraciones, recursos Unitree, instalador, selección de tiros,
  agente arquero, entrada 9A y publicidad.
- Sintaxis del lanzador PowerShell comprobada.
- `pip check`: sin dependencias incompatibles en el entorno privado.
- 138 archivos protegidos de fases históricas y Unitree: SHA-256 antes/después
  idénticos. Los cambios previos de 4A en el working tree se conservaron.
- Visor nativo ejecutado en vivo y cerrado al completar el ensayo; traza idéntica
  al headless. Cierre anticipado comprobado por test con contexto de visor simulado.

Una primera ejecución de tests encontró un bloqueo de permisos del sandbox en
el directorio temporal de Windows. La prueba fue repetida fuera del sandbox y
pasó; el test unitario de bytes se dejó sin depender de ese directorio temporal.
Una invocación de desarrollo desde una carpeta incorrecta falló al importar
`experiments`; los comandos documentados y el lanzador establecen el cwd correcto.
Ninguno de estos fallos fue un resultado físico del robot.

## Evidencia local

`validation/keeper_balance4b/headless_01/` y `viewer_01/` contienen summaries,
trazas NPZ, contactos JSONL y comparación de hashes. Los resultados y el entorno
privado están excluidos de Git por las reglas existentes. No se copió el
checkpoint al paquete. Los PNG se generan desde estados registrados utilizando
el renderizador real de MuJoCo.

Entorno: Python 3.12, PyTorch 2.9.0+cpu, MuJoCo 3.13.0, NumPy 2.5.3,
PyYAML 6.0.3. Se creó e instaló con autorización explícita del usuario.

## Próximo paso recomendado

Mantener este ensayo como baseline de equilibrio libre. Antes de una maniobra,
proponer una prueba independiente de flexión pequeña y retorno, verificando
contactos, transitorios iniciales, saturación y estabilidad. El primer éxito
no autoriza integrar la política en los modos públicos ni atribuirle atajadas.
Los permisos de redistribución del checkpoint siguen pendientes.
