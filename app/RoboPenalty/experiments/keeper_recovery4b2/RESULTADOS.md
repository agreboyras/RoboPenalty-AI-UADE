# Recuperación extendida: diagnóstico detenido por seguridad

Fecha: 30/10/2026. Rama `feature/atajadas-arquero`.

**NO APROBADO.** Se observó recuperación transitoria, seguida de divergencia
articular tardía respecto del baseline y una interrupción por penetración.
El fallo original de 4B.2 se conserva. No se aumentaron amplitudes, ganancias
ni límites; no se habilitó el visor de esta variante.

## Protocolo previo y ejecuciones realizadas

Se fijaron 20 s, con residual cero desde 8 s y evaluación nueva 18–20 s.
Umbral articular conservado: 0.005 rad de error medio absoluto; se añadió,
antes de ejecutar, exigir también máximo <=0.005 rad en esa ventana.
Los demás límites y las amplitudes se importan del protocolo original sin cambios.

Se planificaron tres pares independientes. **Solo se ejecutó el primer par:**
el protocolo detiene las repeticiones si aparece un incumplimiento de seguridad.
Las repeticiones segunda y tercera fueron canceladas; no hay demostración de
reproducibilidad a 20 s. La reproducibilidad original de 10 s no se altera.

| Medición | Baseline nulo extendido | Residual extendido |
|---|---:|---:|
| Pasos | 10000 | 9938 |
| Decisiones | 1000 | 994 |
| Tiempo simulado | 20 s | 19.876 s |
| Tiempo real del bucle instrumentado | 11.120116 s | 11.310399 s |
| Inclinación máxima absoluta roll/pitch | 1.52847° | 3.25401° |
| Deriva máxima | 0.0527744 m | 0.0573142 m |
| Altura mínima de pelvis | 0.7534793 m | 0.7522386 m |
| Torque aplicado máximo absoluto | 29.68601 Nm | 36.34648 Nm |
| Saturación continua | 0 s | 0 s |
| Contactos no pies-suelo | 0 | 0 |
| Penetración máxima | 4.33167 mm | **5.09539 mm** |
| Recortes de referencia | 57 | 68 |
| Fin | Completo, seguro según protocolo | Interrupción por penetración |

Los tiempos excluyen carga/compilación e incluyen instrumentación. No miden FPS
ni permiten atribuir por sí solos costo a la política o al residual.

No hubo caída observada, exceso de torque ni saturación, pero eso no basta para
aprobar. A 19.876 s el contacto del pie izquierdo (`left_ankle_roll_link`) con
el suelo tuvo distancia -0.00509539 m, superando el límite fijo de 0.005 m.
No se ignoró por ser un exceso pequeño. El robot no fue reiniciado ni corregido.

## Evolución del error contra locomoción nula extendida

Errores medios absolutos de rodilla izquierda. Los intervalos siguientes son
descriptivos; la ventana de aceptación 18–20 s no se completó.

| Intervalo observado | Error medio absoluto (rad) |
|---|---:|
| 8–9 s | 0.0092966 |
| 9–10 s, intervalo descriptivo semiabierto | 0.0067015 |
| 10–11 s | 0.0032748 |
| 11–12 s | 0.0011554 |
| 12–13 s | 0.0002579 |
| 13–14 s | 0.0007874 |
| 14–15 s | 0.0010419 |
| 15–16 s | 0.0009764 |
| 16–17 s | 0.0013506 |
| 17–18 s | 0.0027456 |
| 18–19 s | 0.0027876 |
| 19–19.876 s, incompleto | **0.0730385** |

La cifra original 0.00669776 rad usa su ventana cerrada 9–10 s con la muestra
de 10 s incluida. La pequeña diferencia con el intervalo descriptivo semiabierto
de esta tabla procede de ese extremo, no de una modificación de la trayectoria.
Los primeros 10 s de ambos ensayos coinciden exactamente con sus originales.

La rodilla izquierda se acerca al baseline entre 10 y 13 s y luego vuelve a
separarse: no es una recuperación monótona ni un simple offset constante.
En 18–19 s la cadera izquierda ya tiene error medio absoluto de 0.0058655 rad
y máximo de 0.0069234 rad. Por tanto, el requisito de máximo en la nueva ventana
ya estaba infringido antes de la interrupción, aunque no se puede calcular una
media de 18–20 s completa sin las muestras faltantes.

Durante el último intervalo incompleto el máximo de error entre las seis
articulaciones alcanza 0.377837 rad. En el último estado la rodilla izquierda
difiere +0.113415 rad respecto del baseline. No se extrapola qué ocurriría luego.

El baseline tampoco es una postura fija: su pelvis y articulaciones evolucionan.
Por eso la evaluación usa un baseline físico extendido al mismo tiempo.
Ambas ejecuciones empiezan a recortar referencias de tobillo roll derecho al
final: baseline desde 19.00 s y residual desde 18.68 s. Es evidencia de referencias
incompatibles con el rango del modelo en ese período; no identifica por sí sola
la causa raíz de la divergencia. Son hipótesis pendientes la transferencia de
modelo/contactos y la respuesta recurrente de una política sin comando postural.

## Preservación y alcance de las conclusiones

El análisis posterior verifica identidad exacta de los primeros 10 s:
qpos/qvel, torques solicitados/aplicados, controles, referencias y observaciones
para el baseline; y todas las matrices NPZ originales para el residual.
No se usa una trayectoria de referencia futura durante las decisiones.

También se compararon los primeros 5000 registros de contactos de cada caso
contra los archivos originales: posiciones, distancias, fuerzas y clasificación
coinciden exactamente, sin diferencias en baseline ni residual.

El baseline de 20 s completó una ejecución, pero el residual no. No se certifica
robustez global, convergencia asintótica, reproducibilidad extendida ni naturalidad
visual. No se hicieron más ensayos residuales tras activar la interrupción.

Datos locales: `validation/keeper_recovery4b2/headless_01/` y análisis descriptivo
en `validation/keeper_recovery4b2/postmortem_01/`. Los datos se preservan y quedan
excluidos de Git. El postmortem no cambia el informe de aceptación.

## Pruebas y archivos

- 176 tests existentes aprobados (`tests/run_tests.py --include-core`).
- 26 tests experimentales aprobados: siete de 4B.1, siete de 4B.2, ocho nuevos
  del diagnóstico y cuatro del checkpoint externo real. Incluyen ventana
  incompleta, recuperación tardía sin reclasificar el fallo original, desvío
  persistente, oscilación oculta por la media y rechazo del visor sin aprobación.
- Sintaxis del lanzador PowerShell comprobada.
- Bloqueo real del comando de visor comprobado: rechazó el informe fallido antes
  de cargar la política o abrir una ventana. No hubo prueba visual de esta variante.
- 248 archivos previos de código, recursos y resultados históricos conservan
  exactamente sus SHA-256. No se modificaron 4B.1, 4B.2, modos públicos ni externos.
- No se instalaron dependencias ni se ejecutaron comandos Git de escritura.

Solo se creó `experiments/keeper_recovery4b2/` (protocolo, ejecutor, análisis,
tests y documentación) y `scripts/probar_recuperacion_4b2.ps1`, además de los
resultados locales excluidos. La rama sigue siendo `feature/atajadas-arquero`.

## Recomendación

Detener los ajustes residuales sobre esta política de locomoción para preparación
de atajada. Conservar 4B.1 como referencia de equilibrio nominal de 10 s y el
experimento 4B.2 como evidencia de flexión con limitaciones de recuperación.

La próxima investigación debería evaluar `goalkeeper.pt` en su entorno/modelo
de referencia, respetando contrato, contactos, ganancias y permisos existentes,
antes de intentar transferirla a RoboPenalty. Esto no implica que esa política
ya sea compatible o que sus atajadas estén demostradas en nuestro simulador.
