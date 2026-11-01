# Hito 3A: bloqueo central con raíz libre

Experimento privado de contacto, sin nueva maniobra ni agente de selección. Reutiliza exactamente la composición, inicialización, equilibrio, FreeKick y bucle físico H1 mediante una instancia aislada del conductor. No modifica H1, H2, H25, 8C, 9A o 7D.

**Resultado nominal: ATAJADA DEMOSTRADA**, limitada al central evaluado durante 14 s. No demuestra reacción inteligente, extensión de brazos o atajada lateral.

## Ver el ensayo

Desde la raíz de RoboPenalty-AI-Complete, usando la referencia ya obtenida en esta computadora:

```powershell
.\scripts\probar_bloqueo_central_h3a.ps1 -Ubicacion centro -Referencia '.\validation\central_block_h3a\reference_aside_01\interception.json' -Viewer -Camara goal
```

Se observa el tiro central original contra el G1 libre en equilibrio. La pelota rebota en la pierna/pie izquierdos, sin zambullida. Cierra automáticamente tras la evaluación y una pausa final; se puede cerrar la ventana antes, pero ese ensayo será incompleto. Repetir el comando crea una salida fechada nueva. Añadir `-Capturas` guarda imágenes reales y aumenta el tiempo de presentación.

El resultado definitivo está en consola y `interception.json`, después de evaluar toda la ventana. El marcador heredado de H1 no incorpora el contador de atajadas de este experimento: no interpretar su cero como ausencia de contacto. El overlay indica HITO 3A y si ya hubo contacto, sin anticipar una atajada antes de terminar.

Para regenerar ambos ensayos desde cero, elegir una salida nueva para la referencia:

```powershell
.\scripts\probar_bloqueo_central_h3a.ps1 -Ubicacion apartado -Salida '.\validation\central_block_h3a\mi_referencia'
.\scripts\probar_bloqueo_central_h3a.ps1 -Ubicacion centro -Referencia '.\validation\central_block_h3a\mi_referencia\interception.json' -Viewer -Camara goal
```

No reutilizar `mi_referencia` si ya existe; el conductor rechaza sobrescrituras. Sin `-Referencia` se registran contactos/goles pero no se acredita la atajada contrafactual. Para headless, omitir `-Viewer`. Cámaras compatibles: behind, execution, overview, goal y follow.

El lanzador reutiliza los entornos privados H1 y 4B, la importación local FreeKick y el checkpoint externo de locomoción. No instala ni descarga componentes y no copia pesos. Sus rutas relativas son las existentes de esta estación de trabajo; no es un instalador público autónomo.

## Arquitectura y evidencia

- `run.py`: observador de solo lectura alrededor de cada `mj_step` del conductor privado H1. No añade otro controlador, pasos físicos ni fuerzas. Registra contactos sin duplicarlos, impulso estimado fuerza×dt, cruces de planos, distancias, torques y límites. La política sigue recibiendo exclusivamente sus observaciones de equilibrio; la referencia de gol solo se usa al evaluar resultados.
- Mismo PD de H1, comando físico de velocidad `[0,0,0]`, raíz libre, arquero centrado Y=0 o apartado Y=4 para referencia. Tiro exclusivamente `center` del catálogo 8C, sin variar bias ni parámetros.
- `interception_trace.npz`: cada fila contiene tiempo solver, posición/velocidad de pelota antes y después del paso, impulso pelota-arquero, fuerza normal pico y mínima separación geométrica. La traza H1 completa se conserva por separado.
- `ball_keeper_contacts.json`: geometrías y cuerpos involucrados, fuerzas y velocidades por paso. `interception.json`: resultado de la ventana completa y criterios específicos H3A.
- Clasificación reutilizada de `phase4a.evaluation.classify`: un gol prevalece sobre cualquier contacto; SAVE requiere referencia en gol y contacto propio. H3A exige además validez física y cambio de trayectoria. `analyze.py` comprueba igualdad contra referencia antes del contacto, divergencia posterior y reproducibilidad.
- `test_block.py`: nueve pruebas que rechazan falsos éxitos por ausencia de referencia, referencia inválida, contacto seguido de gol, prueba inválida o falta de desvío.

## Criterios y límites

Ventana completa 14 s/7000 pasos. Se mantienen las interrupciones de equilibrio H1: altura >=0.50 m, inclinación <15°, deriva <0.10 m. H3A añade los criterios de impacto ya declarados antes de ejecutar: velocidad articular <=20 rad/s, penetración del arquero <=20 mm, exceso articular <=0.03 rad, torques dentro de caps efectivos y saturación continua <0.10 s. Sin NaN, fuerzas externas ni contactos indebidos.

El reporte H1 original se conserva y puede marcar `feet_only=false` por el contacto esperado con pelota y `keeper_penetration=false` por su antiguo límite de 10 mm. No se modifica ni se presenta como aprobado: los resultados de impacto H3A están separados, con criterio de 20 mm declarado en el protocolo previo. La penetración medida fue 14.59 mm; no se ocultó ni se cambió el criterio después del ensayo.

Ver [RESULTADOS.md](RESULTADOS.md). Todos los datos voluminosos/capturas se guardan bajo `validation/central_block_h3a/`, fuera del contenido publicable. No se actualizaron inventarios históricos ni se integró el experimento en los modos públicos.
