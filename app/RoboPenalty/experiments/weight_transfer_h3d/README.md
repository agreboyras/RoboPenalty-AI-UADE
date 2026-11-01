# Hito 3D: apoyos y transferencia de peso, sin pelota

**NO VIABLE para el protocolo ensayado y el tiempo del penal actual.** Se logró descargar parcialmente el pie derecho, pero la superficie de bloqueo no avanzó 2 cm hacia la trayectoria; el desplazamiento dominante fue contrario. Esto no demuestra imposibilidad de otras estrategias de transferencia o control de apoyo.

## Visualizar

Desde la raíz de RoboPenalty-AI-Complete, un comando por vez:

```powershell
.\scripts\probar_transferencia_h3d.ps1 -Modo baseline -Viewer
.\scripts\probar_transferencia_h3d.ps1 -Modo transfer -Viewer
```

Se abre un laboratorio aislado: **un G1 libre y el suelo físico original, sin pelota, delantero, arco ni estadio**. El overlay muestra fuerzas de cada pie. `baseline` mantiene el equilibrio. `transfer` espera 2 s, introduce las referencias de transferencia y permite observar los posteriores cambios compensatorios de apoyo. No es una atajada ni una prueba integrada de penal.

Cada ejecución simula 6 s y cierra el visor al finalizar. Repetir el comando crea una salida fechada nueva. Cerrar antes la ventana cancela el ensayo y lo deja incompleto; manipular físicamente el robot desde el visor puede aplicar fuerzas externas y lo invalida. Se puede mover la cámara sin intervenir la física. Para headless, omitir `-Viewer`.

El lanzador utiliza los entornos privados MuJoCo y Torch existentes de H1/4B, y recursos externos locales verificados. No instala ni descarga nada ni copia checkpoints. No es un instalador público autónomo. Salidas bajo `validation/weight_transfer_h3d/`, excluidas de Git.

## Arquitectura y conservación

- `scene.py`: compila H1 únicamente como referencia de parámetros y crea en memoria otra composición con un solo G1 original y una copia paramétrica de su suelo. Verifica opciones físicas, gravedad, dt, fricción, parámetros de contacto, geometrías, articulaciones, masas, inercias y actuadores. El modelo ejecutado tiene nq=36, nv=35, nu=29, una raíz libre y cero igualdades. No se exportan XML ni se modifican assets externos.
- `run.py`: misma política de equilibrio de locomoción, comando físico cero, estado recurrente reiniciado por ensayo y normalizador congelado. Un único PD escribe los 29 actuadores. No escribe posiciones/velocidades de raíz tras inicializar ni usa fuerzas externas. Preparación y límites de impacto se conservan; una caída posterior al inicio no se oculta ni corrige.
- `support.py`: fuerzas nativas del solver por pie, centro de presión estimado por fuerzas verticales, centro de masa real del subárbol G1, polígono de contactos con Fz>1 N y margen de la proyección del CoM. Estar dentro del polígono no garantiza estabilidad dinámica; fuera de él tampoco equivale por sí solo a caída.
- `maneuver.py`: referencias quínticas de transferencia, ambas caderas roll -0.12 rad y ambos tobillos roll +0.12 rad, sin cambiar ganancias o caps. Rampa 0.35 s, mantenimiento hasta 1.2 s desde la orden y retirada 0.50 s. La amplitud se eligió tras el diagnóstico estático, antes de probar movimiento. La lógica de posible liberación/bloqueo posterior no se habilitó en el lanzador ni se ensayó físicamente: su condición de avance temprano no se cumplió. No se aumentaron amplitudes ni se cambió ese umbral para avanzar.
- `analyze.py`: medidas posteriores de descarga, separación de pie, desplazamiento firmado del punto material de pierna, tiempos, repetibilidad y conservación. Nunca alimenta el controlador con resultados futuros.
- `render.py`: renderizador MuJoCo de estados grabados, sin política ni integración. Restaura qpos/qvel solamente en datos de render independientes. El contraste de iluminación y color del suelo se aumenta exclusivamente en ese renderizador; no altera las pruebas físicas.

## Qué se mide

La pierna de bloqueo es la derecha anatómica, situada en +Y mundial; el arquero mira -X. El objetivo lateral de comparación es +Y. Se sigue un punto material de la malla de pierna inferior que produjo el contacto H3B. No es un nuevo colisionador ni una animación.

Descarga parcial: media móvil de 40 ms con pie derecho <=30% del total y <=65% de su carga basal, izquierdo >=55% del peso total; mantenimiento de la condición 40 ms. El lazo de observación a 50 Hz recibe la fuerza del paso físico precedente, sin utilizar información futura. Se registra también toda pérdida transitoria de fuerza, sin confundirla con liberación sostenida.

Liberación con margen: pie derecho <=10% de su carga basal y separación mínima de todas sus esferas de suela >=2 mm durante 20 ms, con apoyo suficiente en el izquierdo. Ese margen estaba declarado antes de ejecutar y no es la única evidencia: también se miden fuerzas cero y separaciones menores.

Tiempos 2/5/10 cm: desplazamiento **firmado hacia +Y**, desde la posición al iniciar. No se cuentan movimientos de igual magnitud en sentido contrario. Se compara además contra baseline al mismo instante. El presupuesto es 0.90 s desde detección para el plano nominal (0.94-0.04), y conservadoramente 0.874 s para la superficie que tocaba la pelota en H3B (0.914-0.04). Estos tiempos proceden de ensayos anteriores; aquí no hay detector de pelota porque no hay pelota.

Para proponer una futura prueba con pelota se exigía, antes de ejecutar: descarga y liberación medidas, movimiento del punto >=2 cm hacia +Y y ganancia >=1.5 cm respecto del baseline, altura útil 0.03–0.23 m, antes de caer y dentro de 0.874 s, además de validez física. No se cumplió. Los 5/10 cm son medidas adicionales, no requisitos ocultos.

## Límites físicos

dt=0.002 s, 500 Hz de PD y 50 Hz de inferencia. Sin cambios de torque/gain: caps efectivos del G1/4B. Límites de aceptación: velocidad articular <=20 rad/s, penetración <=20 mm, exceso articular <=0.03 rad y saturación continua <0.10 s. Interrupción: 40 rad/s, 30 mm, 0.10 rad o saturación >=0.50 s, además de fuerzas externas o estado no finito. Antes de la orden se exige altura >=0.50 m, inclinación <15° y deriva <0.10 m. Después se permiten desplazamiento y caída; se registra caída con altura <0.50 m o inclinación >=45°.

## Archivos y reproducibilidad

`trace.npz` guarda por separado qpos, qvel, política original, residual, referencia final, torque pedido/enviado/real, fuerzas por pie, CoM, CoP, apoyo, separación de suelas y puntos físicos. `contacts.json` conserva los contactos con fuerzas y distancias. Los estados geométricos y fuerzas son del tiempo solver anterior a integrar; no se mezcla esa geometría con un estado posterior.

`configuration.json` y `planner.json` conservan parámetros y transiciones; `comparison.json` conserva tiempos, resultados y SHA-256 de preservación. Los soportes iniciales indefinidos (pies aún 1 mm sobre suelo) se representan como NaN solo en CoP/margen, no en estados físicos. Su igualdad se comprueba como dato indefinido equivalente, mientras qpos/qvel y demás matrices físicas se comparan estrictamente.

Ver [RESULTADOS.md](RESULTADOS.md). No se ejecutó ningún penal ni se avanzó a otra estrategia.
