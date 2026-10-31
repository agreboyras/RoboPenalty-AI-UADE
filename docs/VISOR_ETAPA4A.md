# Observar 4A en vivo, antes de decidir la etapa siguiente

El visualizador original `visualize.py` solo genera PNG de snapshots. `run_trial.py` tampoco tenía visor. Se agregó una entrada privada mínima que reutiliza el visor pasivo, protecciones, cámaras y cierre de 7D, sin editar 8C, 9A o 7D ni agregar habilidades.

## Probar ahora en esta computadora

La carpeta principal auditada tiene el contenido público (78/104), sin `.venv` ni los 26 recursos importados. Para evitar instalar o buscar recursos en otros proyectos, hay una copia de validación completa, preparada dentro de este mismo proyecto. Usa el entorno previamente validado; no es una instalación nueva ni una distribución autónoma para terceros.

Abrir PowerShell en `RoboPenalty-AI-Complete`, la carpeta que contiene `app/` y `scripts/`:

```powershell
$ver4a = '.\validation\keeper_live_20261030\ver_local.ps1'

# 1. Referencia estable: el arquero mantiene la guardia.
& $ver4a -Ensayo sin-pelota

# 2. LEFT y RECOVERY, en una nueva ventana.
& $ver4a -Ensayo sin-pelota -Lado LEFT -Experimental

# 3. RIGHT y RECOVERY.
& $ver4a -Ensayo sin-pelota -Lado RIGHT -Experimental

# 4. Un tiro FreeKick real del catálogo, con el arquero experimental.
& $ver4a -Ensayo tiro -Accion right_inter_m080 -Experimental -Camara goal
```

Ejecutar **una orden por vez** y esperar a que termine o cerrar la ventana antes de pasar a la siguiente. `LEFT` y `RIGHT` son los lados del campo desde el delantero mirando al arco; no los lados anatómicos del G1 que está de frente.

El helper local y sus recursos están bajo `validation/`, excluido de Git. No se incorporan los recursos externos a la distribución pública. Si se mueve o elimina esa validación, usar la instalación normal que sigue.

## Instalación normal completa de la rama

Cuando esta carpeta tenga su propio `.venv` y el diagnóstico indique 104/104, desde la misma raíz usar:

```powershell
$ver4a = '.\scripts\ver_arquero_4a.ps1'
& $ver4a -Ensayo sin-pelota
& $ver4a -Ensayo sin-pelota -Lado LEFT -Experimental
& $ver4a -Ensayo sin-pelota -Lado RIGHT -Experimental
& $ver4a -Ensayo tiro -Accion right_inter_m080 -Experimental -Camara goal
```

El lanzador usa las verificaciones existentes y admite `-Python` con un ejecutable real. No obtiene dependencias ni busca carpetas externas por su cuenta. La instalación habitual se documenta en [INSTALACION_WINDOWS.md](INSTALACION_WINDOWS.md).

## Qué observar

**Sin pelota:** se reutiliza exactamente el ensayo físico de laboratorio. Pelota y delantero permanecen apartados desde la inicialización. Se ve el G1 completo, con cámara cercana y decoración liviana para reducir el costo gráfico. No se pretende ver una atajada autónoma en este ensayo temporizado.

- De 0 a 2 segundos simulados: guardia.
- De 2 a 5: extensión moderada del lado elegido, si se pasó `-Experimental`.
- De 5 a 10: retorno suave a la guardia, con estado `RECOVERY`.
- Sin `-Experimental`: mantiene la postura estable; no hay extensión que recuperar.

La consola muestra `WAIT`, `LEFT` o `RIGHT`, y `RECOVERY`, junto con el tiempo simulado. La maniobra es pequeña: no hay salto, caída ni inclinación de la pelvis. Brazos, torso y piernas se mueven por dinámica y torques del controlador existente; no se reproduce un archivo de poses.

**Tiro:** se mantiene el estadio completo y se ejecuta un penal real de 14 s simulados, con FreeKick, predictor, B y recuperación de 8C. `-Camara goal` permite observar arquero, pelota y delantero desde el lado del arco. El resultado se calcula físicamente. En la validación de esta orden, `right_inter_m080` terminó en gol; no hay evidencia nueva de atajada con el brazo.

Para observar una acción que en la referencia termina en atajada de pie/tobillo:

```powershell
& $ver4a -Ensayo tiro -Accion left_near_b060 -Experimental -Camara goal
```

Para comparar el **mismo tiro** con la postura estable, omitir el switch, conservando acción y cámara:

```powershell
& $ver4a -Ensayo tiro -Accion right_inter_m080 -Camara goal
```

La maniobra del ensayo sin pelota usa una consigna temporizada de laboratorio; durante el tiro, la reacción proviene de observaciones y predicción actuales, sin recibir la etiqueta del preset.

## Cámaras, velocidad y cierre

- `-Camara keeper`: vista cercana diagnóstica del arquero; predeterminada sin pelota.
- `-Camara behind`: vista de estadio detrás del delantero; predeterminada para el tiro.
- También se aceptan `execution`, `overview`, `goal` y `follow`.
- La cámara se elige al lanzar el ensayo. No se agrega un menú ni se cambian las cámaras públicas.
- Objetivo de reproducción **1×**, sin multiplicador ni saltos de pasos físicos. Si la máquina no sostiene tiempo real puede ir más lento; no se ocultan pasos para compensarlo. La verificación de hashes y el arranque agregan tiempo antes de ver movimiento. El reloj de consola/overlay es tiempo simulado.
- Cerrar con la **X** de la ventana o con **Ctrl+C** en la consola. Un ensayo interrumpido antes de completarse no se presenta como aprobado ni se le inventa un resultado. Cerrar durante la pausa final conserva el resultado físico ya completado.
- Tras completar la prueba, el visor sostiene el resultado aproximadamente dos segundos y se cierra solo. Repetir la misma orden abre otro ensayo con condiciones iniciales nuevas y crea otra carpeta de resultados con fecha/identificador; no sobreescribe el anterior.
- Los controles por texto de la partida pública no se implementan aquí. No hay que escribir `Iniciar partido`: el ensayo seleccionado comienza automáticamente.

## Implementación y comprobaciones

- Nuevo `experiments/keeper_saves/live_viewer.py`: reutiliza `MonumentalPresenter` y el cierre de su hilo de renderizado; siempre dibuja el mismo modelo/datos que se simulan.
- `run_trial.no_ball` admite un observador opcional, nulo por defecto. Con visor no recalcula el barrido geométrico en cada snapshot; conserva los estados, torques y telemetría. El mapa completo sigue disponible en el ensayo offline.
- Nuevo `scripts/ver_arquero_4a.ps1`: entrada privada con preflight y argumentos explícitos.
- No se editaron 8C, 9A, 7D, publicidad, IA, XML, políticas ni lanzadores públicos.
- Se comprobaron ventanas nativas de guardia, LEFT, RIGHT y un tiro experimental, incluyendo cierre del render thread. También se comprobó el helper local listo para usar.
- Tests privados: nueve, incluidos valores predeterminados de cámara y cierre/interrupción con preservación del resultado completado. Se conserva la batería estable.

Validación final: **176 regresiones estables y nueve tests privados aprobados**. Se completaron seis ventanas nativas (comparaciones iniciales y LEFT/RIGHT con decoración liviana), con cierre correcto. Las posiciones, velocidades, referencias y torques registrados del ensayo sin pelota coincidieron exactamente con 4A offline; las trazas, contactos, decisiones y estado final del tiro coincidieron con su referencia experimental. No se comparan como física los tiempos reales ni el barrido geométrico omitido durante la visualización.

Resultados y comparación con los estados offline de 4A quedan en `validation/keeper_live_20261030/`. Las salidas interactivas se crean en `experiments/keeper_saves/results/live_*`, excluidas de Git. No se integró ninguna nueva habilidad ni se avanzó a 4B.
