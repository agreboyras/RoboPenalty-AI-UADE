# Instalación guiada: prueba nueva del 30/10/2026

## Qué se implementó

Instalación guiada mediante `instalar.ps1`: comprueba Windows, CPython 3.12 x64 y PowerShell >=5.1; resume los pasos autorizados; ofrece una entrada de carpeta cuando la consola es interactiva y faltan recursos; conserva `-DeployPath` y agrega `-Interactivo`/`-NoInteractivo`. Si ya hay una importación válida no vuelve a pedir la fuente. Los hashes, avisos, bloqueo de descargas pendientes y habilitación estricta de 104/104 se conservan. El diagnóstico muestra el conteo de recursos.

La selección de entrada y la validación del estado parcial están separadas en `_install_input.ps1`. ENTER no habilita descargas ni marca éxito: prepara lo disponible y retorna 2. Errores de integridad, faltantes ajenos o duplicados se rechazan. No cambió física, agentes, políticas ni calibraciones.

## Obtención de recursos: resultado concreto

La documentación oficial y los manifiestos identifican 15 originales compartidos, ocho modificaciones TP07 y tres adiciones. El árbol remoto de TP07 en ce4b34d1bccfd0420a81bf1688271d86feb8a117 contiene los 26 paths con los blobs Git esperados, incluidos ONNX y NPZ. Esta verificación de disponibilidad técnica no se presenta como verificación SHA-256 de una descarga nueva ni como autorización.

Las condiciones de los 26 recursos siguen pendientes para una descarga/redistribución general; no se habilitó esa descarga ni se distribuyeron archivos o parches. Una copia oficial sola no basta. La guía identifica la revisión TP07 y su ZIP fijo como fuente técnica condicionada a contar con derechos de acceso/uso aplicables. El equipo debe resolver y comunicar esa vía autorizada a cada integrante. Hasta entonces, GitHub solo no permite jugar; sí permite preparar el entorno, correr los tests y estudiar código/resultados. Una demostración en una instalación que ya disponga legítimamente de recursos evita reenviar los binarios.

## Carpeta limpia y aislamiento

Se creó una carpeta nueva con espacios en el nombre, usando exclusivamente los archivos del inventario publicable, sin `.git`, `.venv` o caches previos. No se clonó un nuevo repositorio. Se creó un .venv nuevo con el lock PyPI y sin paquetes de sistema.

Antes de las pruebas se preparó por separado una carpeta de recurso local suministrado explícitamente, extrayendo los bytes de la revisión TP07 local ya disponible y comprobando los 26 SHA-256. Esa preparación de fixture no forma parte del instalador ni demuestra una adquisición autónoma de recursos por otro alumno. El instalador no recibió esa carpeta hasta la fase de importación explícita.

Durante las tres tandas se ejecutaron los lanzadores PowerShell reales con un envoltorio de instrumentación Python, solo en validation. Bloqueó aperturas Python hacia el proyecto original, Deploy original, Unitree original, copia de portabilidad, carpetas de validación anteriores, paquete app de trabajo, carpeta fuente suministrada y site-packages del Python base. Los seis registros del guard confirmaron el prefijo del entorno nuevo y cero violaciones. Los recursos de ejecución se resolvieron en la copia nueva; no se usaron entornos anteriores. La comparación posterior leyó solamente JSON de mediciones del baseline, fuera de la ejecución aislada.

Es una simulación de la distribución preparada localmente, no una prueba de clonar una versión todavía no publicada de estos cambios. La URL pública y su rama main se comprobaron; no se ejecutó Git clone ni se creó otro repositorio. La prueba no representa otra computadora física.

El lanzador `py -3.12` no encontró un Python registrado en esta sesión. El bootstrap usó explícitamente un ejecutable CPython 3.12 x64 base, sin usar entornos de los proyectos. La creación del entorno y las pruebas siguientes fueron reales. No se declara comprobada la detección de un Python registrado ni se instala Python globalmente; README y guía incluyen `-Python` con selección explícita.

## Instalación y mensajes medidos

| Caso | Código | Resultado | Tiempo real |
|---|---:|---|---:|
| Sin Deploy, `-NoInteractivo`, entorno nuevo | 2 | Paquetes listos, 78/104, juego bloqueado | 159,64 s |
| Carpeta suministrada explícitamente, ruta con espacios | 0 | 104/104 e instalación local apta | 8,50 s |
| Diálogo real `Read-Host`, ENTER sin carpeta, solo recursos | 2 | Parcial 78/104 | 11,23 s |
| Diálogo real, carpeta entre comillas y con espacios, solo recursos | 0 | 104/104; comprobación de paquetes separada | 9,75 s |

Los tiempos son mediciones individuales en este equipo/conexión, no un plazo universal. La primera instalación sin Deploy incluyó descarga de paquetes desde PyPI; la segunda reutilizó únicamente los paquetes de ese entorno recién creado. Las pruebas de diálogo usaron otra copia pública nueva y el mismo Python nuevo explícito, sin pip.

## Tandas ejecutadas

| Caso | Pasos | Goles / atajadas / errados | Sesión Python | Lanzador completo | Comparación 8C |
|---|---:|---|---:|---:|---|
| Automático headless | 35.000 | 3 / 2 / 0 | 52.89 s | 70.38 s | Exacta |
| Dirigido con entrada real de consola | 35.000 | 3 / 2 / 0 | 48.17 s | 57.48 s | Exacta |
| Automático con visor | 35.000 | 3 / 2 / 0 | 128.49 s | 136.11 s | Exacta |

Cada tanda simuló 70 segundos. Secuencia comparable: right_inter_m080, right_open_m100, right_corner_m140, left_near_b060, center. Resultados: GOAL, GOAL, GOAL, SAVE, SAVE. En dirigido se alimentaron seis líneas de texto por stdin: inicio y cinco tiros, esperando sus mensajes reales de solicitud. No se adelantaron órdenes ni se seleccionó el tiro mediante información futura.

Cero diferencias en los campos comparados: hashes/estados iniciales, trazas de pelota, contactos, evaluación física, movimiento/decisiones del arquero, postura, retorno, monitor, estado completo final de integración y clasificación. Se compararon los sidecars registrados, sin tolerancias nuevas; no se afirma equivalencia de toda variable no registrada en cada paso. Se excluyeron tiempos reales, rutas/identificadores de proceso y el conteo de recursos del perfil 104 frente al histórico 209.

Los cinco tiros de cada tanda tuvieron contacto pie-pelota, sin caídas del delantero ni errores del runtime; los monitores del arquero coincidieron con el baseline estable. El aprendizaje automático coincidió con 8C; el modo dirigido dejó cinco entradas manuales sin historial automático. Voz desactivada. El visor usó el mismo mundo, cerró correctamente y terminó su hilo de renderizado (2.538 sincronizaciones). Los tiempos con visor incluyen presentación y pacing; no son FPS ni costo aislado del render.

## Tests y verificaciones

**144 tests aprobados en la copia nueva:** los 134 anteriores y diez nuevos del instalador: opciones excluyentes, detección sin consola, interacción forzada, rutas explícitas con espacios, omisión del diálogo cuando está completo, modo sin preguntas, recorte de comillas, ENTER vacío y rechazo de estados con errores/duplicados/faltantes inesperados. Los tests PowerShell usan RemoteSigned solo en el proceso hijo, sin modificar políticas globales.

Los logs, fixtures, entornos y pruebas crudas quedan en `validation/student_20261030`, fuera de Git. Los 26 recursos importados permanecen ignorados; las 37 calibraciones y manifiestos conservan los hashes. El inventario se renueva solo para cambios propios de instalación/documentación.

## Pendiente antes de compartir esta revisión

Publicar manualmente estos cambios (esta sesión no hizo add, commit, push ni cambió remotos). Confirmar la vía autorizada de acceso/uso de Deploy para el grupo. Probar otra computadora Windows. La voz sigue pendiente y no se habilitó. La licencia del código propio sigue por acordar; se conservaron las atribuciones y las licencias BSD incluidas. No es una instalación totalmente autónoma a partir de GitHub.

La revisión sintáctica pasó para ocho scripts PowerShell y veintidós bloques de comandos del README/guía. La disponibilidad de los 26 blobs TP07 fue verificada contra los identificadores Git del manifiesto; no se descargó ese conjunto por red. Los comandos de instalación/juego se probaron sobre la copia limpia preparada localmente. La alternativa Git clone está documentada, pero no se ejecutó por la restricción de no crear otro repositorio.
