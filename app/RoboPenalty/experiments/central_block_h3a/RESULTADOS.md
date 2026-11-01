# Resultados Hito 3A

Fecha: 2026-10-31. **ATAJADA DEMOSTRADA para el central nominal en la ventana de 14 s.** Bloqueo pasivo físico con raíz libre; no es una atajada lateral ni una decisión autónoma.

## Configuración fijada antes de ejecutar

Composición y conductor físico H1 intactos. Misma inicialización long, central 8C bias 0, pelota y colisiones originales. Arquero en X=4.2, Y=0, frente -X, altura inicial efectiva 0.7794213197 m. Referencia con el mismo G1 en Y=4. Sin slider, fuerzas externas, nuevas referencias articulares o política 4C. Un PD del arquero a 500 Hz con inferencia auxiliar de equilibrio a 50 Hz, velocidad física deseada cero, normalizador congelado y estado recurrente reiniciado al comienzo.

Ventana 14 s, 7000 pasos por ejecución. Se ejecutó B inicial (`center_00`) y **tres repeticiones adicionales** para cubrir explícitamente los apartados B y C solicitados; luego una ejecución con visor/capturas. Un solo proceso de simulación física por ensayo.

## Resultados nominales

| Ejecución | Impacto delantero, tiempo solver | Primer contacto G1 | Muestras de contacto | Fuerza normal pico | Gol durante 14 s | Resultado |
|---|---:|---:|---:|---:|---|---|
| A, reference_aside_01 | 4.174 s | Ninguno | 0 | 0 N | Sí | GOAL |
| B, center_00 | 4.174 s | 4.910 s | 8 | 564.96 N | No | SAVE |
| C1, center_repeat_01 | 4.174 s | 4.910 s | 8 | 564.96 N | No | SAVE |
| C2, center_repeat_02 | 4.174 s | 4.910 s | 8 | 564.96 N | No | SAVE |
| C3, center_repeat_03 | 4.174 s | 4.910 s | 8 | 564.96 N | No | SAVE |
| Visual, center_viewer_01 | 4.174 s | 4.910 s | 8 | 564.96 N | No | SAVE |

Las ocho muestras no son ocho impactos independientes: incluyen seis muestras de pierna inferior `gk/left_knee_link` y dos de pie `gk/left_ankle_roll_link`, entre 4.910 y 4.920 s. El primer punto de contacto es aproximadamente `(4.12705,-0.12261,0.15395)` m. `left_knee_link` nombra el cuerpo del colisionador extendido por la pierna inferior, no implica choque contra el centro anatómico de rodilla.

Referencia: cruza X=4.2 a 4.9443346 s y X=5 a 5.1125733 s, dentro del arco, Y=-0.11446445 m, Z=0.11499728 m. El tiro centrado es interceptado **antes de llegar a X=4.2**: su centro alcanza como máximo X=4.0319442 m. No debe inventarse un tiempo de cruce de ese plano para el ensayo bloqueado.

Convención temporal: el solver detecta el primer contacto pie-pelota a 4.174 s; el estado después del paso se registra a 4.176 s. La llegada de referencia a X4.2 es 0.770335 s desde el tiempo solver o 0.768335 s desde el registro posterior al paso. Esto es coherente con los ~0.768359 s de la auditoría anterior: además de esos 2 ms de convención, aquella interpolaba la traza de 50 Hz; aquí se interpolan pasos de 500 Hz. No se alteró el tiro para ajustar los tiempos.

## Desvío físico

- Antes del primer contacto con G1, pelota **y delantero** coinciden bit a bit con la referencia apartada, en las muestras guardadas. La variación de ubicación del arquero no cambia el tiro antes de interceptarlo.
- Inmediatamente antes del primer choque: velocidad pelota `(5.18624,-0.03094,0.00323)` m/s.
- Después de ese paso: `(2.75392,+0.17139,0.00693)` m/s. La diferencia respecto del paso correspondiente de la referencia es 2.43316 m/s.
- A 4.922 s: `(-1.39958,+0.59239,+0.06812)` m/s. La velocidad longitudinal ya es negativa: rebota hacia el delantero.
- Impulso pelota-arquero integrado como suma de fuerzas de contacto×0.002 s: aproximadamente `(-2.70042,+0.31876,-1.15469)` N·s. Es una estimación discreta de estos contactos, no el impulso total sobre la pelota: también actúa el suelo y otras fuerzas originales. Por ello la componente vertical no equivale directamente a masa×cambio de velocidad vertical.
- Posición final de pelota a 14 s: `(2.13616,+0.13335,0.11500)` m. No hubo cruce válido de gol durante la ventana completa.

La clasificación usa `phase4a.evaluation.classify` sin modificarla: referencia con gol + contacto verificado + ausencia de gol. H3A exige adicionalmente cambio de trayectoria y validez física. No se clasifica una ausencia de gol sin contacto como SAVE.

## Estado físico del G1

Los resultados centrados son idénticos:

| Métrica | Medido | Criterio declarado antes de ejecutar |
|---|---:|---:|
| Inclinación máxima | 1.902° | <15° |
| Deriva horizontal máxima | 0.03439 m | <0.10 m |
| Altura mínima de pelvis | 0.76740 m | >=0.50 m |
| Velocidad articular máxima | 5.3803 rad/s | <=20 rad/s |
| Exceso articular máximo | 0 rad | <=0.03 rad |
| Penetración máxima del arquero | 14.586 mm | <=20 mm |
| Saturación continua máxima | 0 s | <0.10 s |

Sin caídas, NaN, advertencias numéricas MuJoCo, contactos inesperados, fuerzas externas o violaciones de caps efectivos de torque. Los 29 picos de torque y sus caps están en `interception.json`. Se mantienen seis recortes iniciales de referencias de política ya presentes en H1; no se agregaron recortes específicos para provocar el bloqueo.

La consola conserva un aviso de migración de Hydra del Deploy externo sobre `version_base`; no es una advertencia numérica de MuJoCo ni impidió ejecutar. No se modificó ese recurso externo para silenciarlo.

**Transparencia sobre H1:** su reporte `report.json` permanece con `success=false` en los centrados por `feet_only` y `keeper_penetration`. La primera condición trata cualquier pelota-arquero como impropia porque H1 evaluaba equilibrio sin intercepción; la segunda usa 10 mm. No se reescribió el reporte ni su código. H3A define antes de ejecutar contactos de pelota esperados y el límite de impacto 20 mm heredado del diagnóstico/H25. Las interrupciones de equilibrio de H1, la física y todos los límites de torque permanecen activos. La penetración de 14.6 mm debe considerarse al evaluar la calidad del contacto; no se afirma contacto sin penetración.

No se registraron choques del arquero con cajón posterior, postes o red. El bloqueo se produce delante de esos elementos, sin caída. Los postes y la red siguen siendo visuales sin colisiones.

## Reproducibilidad y visualización

Tres repeticiones adicionales: igualdad bit a bit de `keeper`, `decisions`, `ball`, `shooter` y `stability` respecto de `center_00`. La ejecución con visor/capturas también coincide exactamente en los cinco arrays. Los estados iniciales y las comprobaciones de composición H1 se conservaron.

Se abrió el visor nativo y se generaron doce capturas reales (inicial, primer contacto, final, por cuatro cámaras). Se inspeccionaron `first_keeper_contact_behind.png` y `first_keeper_contact_goal.png`: estadio, ambos G1, pelota y contacto bajo visibles. Esto es verificación técnica de ejecución/render; la evaluación visual personal del usuario sigue disponible mediante el lanzador.

No hay recuperación o zambullida: el G1 bloquea manteniendo equilibrio. El marcador heredado H1 no suma SAVE de este experimento; el resultado autoritativo se imprime por consola y se guarda tras la ventana completa. La presentación pública 7D no fue modificada para cambiar ese contador.

## Rendimiento medido

| Ejecución | Total real | Bucle físico y diagnóstico |
|---|---:|---:|
| Referencia apartada | 29.729 s | Consultar reporte |
| B centrado inicial | 22.608 s | 11.676 s |
| Repetición 1 | 26.658 s | 15.212 s |
| Repetición 2 | 24.359 s | 13.469 s |
| Repetición 3 | 23.345 s | 11.911 s |
| Visor y capturas | 43.227 s | 21.049 s |

Todos simulan 14 s. El total incluye arranque e inferencia auxiliar; el bucle incluye medición de distancias/contactos, RPC y presentación si corresponde. No son FPS ni una medición aislada de renderizado. Hubo otros tests ejecutándose durante parte del trabajo; no inferir diferencias de rendimiento físico entre repeticiones idénticas.

## Tests y conservación

- 9 tests de clasificación/protocolo H3A + 20 de H1/H2/H25: **29 aprobados**.
- Suite de distribución y núcleo: **176 aprobados**.
- Sintaxis del nuevo PowerShell: correcta.
- Verificaciones previas H1: 104 recursos exactos y calibración central con SHA-256 válido en cada ejecución. Sin archivos externos modificados durante los ensayos.
- 25 archivos fuente/documentación H1/H2/H25 y 258 archivos previos protegidos: mismos SHA-256 antes/después.
- No se ejecutaron tandas públicas de cinco ni se integró H3A en ellas; esas capacidades no forman parte de esta prueba de un penal. No se ejecutó Git de escritura.

Datos completos: `validation/central_block_h3a/comparison.json`, `comparison.log`, cada `interception.json`, `ball_keeper_contacts.json`, ambas trazas NPZ y capturas. Los reportes históricos se conservan intactos.

## Conclusión limitada

La hipótesis geométrica del central se confirmó físicamente en estos ensayos nominales: un G1 libre y equilibrado bloquea el balón con pierna/pie, el balón rebota y no entra durante 14 s. La evidencia respalda **ATAJADA DEMOSTRADA**, sin afirmar robustez a perturbaciones, inteligencia reactiva de atajada, capacidad lateral o naturalidad humana. No se avanza a otra estrategia sin autorización.
