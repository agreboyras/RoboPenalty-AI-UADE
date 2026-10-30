# Etapa 2: validación final de importación LF/CRLF

Fecha: 30/10/2026. Resultado: **validación técnica aprobada; cambios locales, todavía sin publicar**.

## Instalación nueva y aislada

Se copiaron los 235 archivos del inventario publicable a una carpeta nueva con espacios en su nombre, sin `.git`, entorno virtual ni los 26 recursos pendientes de Deploy. Estado inicial: **78/104**. Este informe se agregó después de las pruebas; no cambia código ejecutable.

Se ejecutó el instalador PowerShell real, sin `-SoloRecursos`, con `-NoInteractivo`, un intérprete CPython 3.12.14 explícito y la carpeta original de Deploy como fuente local. Se creó un entorno virtual nuevo, con `include-system-site-packages = false`, y se instalaron los 19 paquetes de ejecución fijados. No se reutilizó ningún entorno virtual de los proyectos anteriores.

El instalador terminó con código **0** en **182,74 s**. Importó 26 recursos: **21 textos CRLF se copiaron como LF canónico y cinco recursos ya eran exactos**. Para cada salida se comprobó el SHA-256 esperado; también se contrastó el hash bruto del origen con el registro de importación. Los binarios ONNX y NPZ permanecieron sujetos a coincidencia exacta de bytes. No se modificó el origen.

El diagnóstico posterior, usando automáticamente el entorno virtual nuevo, confirmó **104/104**, inventario y paquetes correctos, e `execution_ready: true`. Conserva `distribution_ready: false`: la importación local no concede derechos de redistribución.

Limitación del entorno: se proporcionó explícitamente el intérprete porque el lanzador `py` de esta computadora no tenía una instalación 3.12 registrada. No se validó aquí la selección automática mediante `py -3.12`. La instalación de paquetes requirió acceso de red autorizado; no se requiere red para ejecutar la simulación ya instalada.

## Pruebas y simulación

Los **170 tests** del paquete y del núcleo pasaron dentro del entorno nuevo. Se ejecutaron los lanzadores PowerShell reales sin alterar las órdenes de simulación.

| Modalidad automática | Resultado por penal | Marcador | Tiempo simulado | Pasos | Tiempo de sesión | Proceso del lanzador completo |
|---|---|---|---:|---:|---:|---:|
| Headless | GOAL, GOAL, GOAL, SAVE, SAVE | 3 goles, 2 atajadas, 0 errados | 70 s | 35.000 | 61,10 s | 77,37 s |
| Visor MuJoCo | GOAL, GOAL, GOAL, SAVE, SAVE | 3 goles, 2 atajadas, 0 errados | 70 s | 35.000 | 120,13 s | 132,08 s |

Los tiempos de sesión y de proceso son mediciones distintas. No se separó el costo exclusivo de renderizado, ni se midieron FPS. No se atribuye toda la diferencia al renderizado.

Acciones en ambas tandas: `right_inter_m080`, `right_open_m100`, `right_corner_m140`, `left_near_b060`, `center`.

Cada penal registró contacto pie–pelota, pasó los controles físicos y no registró caída del delantero ni fallo de simulación. Los monitores articulares y las trazas de postura coinciden con la referencia. Apareció el aviso de compatibilidad `version_base` de Hydra ya conocido; no hubo excepciones nuevas.

El visor usó el mismo mundo físico, permaneció abierto entre penales y registró **2.443 sincronizaciones**. El cierre del visor, su hilo de renderizado y el trabajador de consola quedaron confirmados en el resumen de sesión. La voz permaneció desactivada. No se generaron nuevas capturas RGB en esta validación.

## Comparación exacta

Ambas tandas se contrastaron por separado contra los JSON medidos de 8C y de la instalación aislada anterior: **cero diferencias** en los campos comparados, sin tolerancias nuevas.

La comparación incluyó configuración y escenario, hash y valores del estado inicial, estado completo de integración final, evaluación y contactos, guía lateral, trazas de pelota y observaciones del agente, datos de tiro, planificación, postura, retorno, monitor motor y estadísticas de aprendizaje. Se verificaron los 35.000 pasos. Por lo tanto también coinciden esas trazas entre visor y headless.

La identidad se refiere a esos registros y muestras disponibles; no a todos los estados intermedios no guardados. Se excluyeron deliberadamente tiempos reales, rutas de salida, identificadores de proceso/objetos y metadatos de distribución que no representan física. No se confundió igualdad de marcador con equivalencia de trazas.

Durante la ejecución se bloquearon accesos Python a los proyectos originales, al clon de prueba, a las validaciones anteriores y al código de la distribución madre. Cuatro procesos instrumentados confirmaron entorno nuevo y cero accesos prohibidos. Esta instrumentación no es un monitor de archivos nativo del sistema operativo. Las referencias anteriores se leyeron como datos JSON únicamente después de jugar.

## Conservación de originales y publicación

Se verificaron antes y después los SHA-256 de 700 archivos: 190 de Deploy, 275 del RoboPenalty original y 235 del clon de prueba, incluidos los recursos requeridos y los metadatos Git seleccionados. **Cero cambios**. El alcance corresponde a los archivos controlados; no constituye un inventario de todos los cachés o archivos ignorados de esas carpetas. No se ejecutaron operaciones de escritura sobre ellas.

El manifiesto histórico de 209 recursos y el perfil de ejecución de 104 conservan sus hashes. El inventario público actualizado enumera cada archivo y su SHA-256; excluye su propia entrada. El paquete publicable conserva los 37 JSON de calibración, catálogo, licencias y recursos autorizados. Los 26 recursos pendientes, los entornos, registros con rutas locales, resultados de tandas y herramientas de esta validación permanecen fuera de Git.

### Cambios exactos para una publicación posterior

Comparados con el HEAD local, corresponden estos 16 archivos; **no** todo el contenido del directorio de validación:

```text
README.md
THIRD_PARTY.md
app/RoboPenalty/portability/distribution_profile.json
app/RoboPenalty/portability/external_sources.json
app/RoboPenalty/portability/install_resources.py
app/RoboPenalty/portability/local_import.py
app/RoboPenalty/portability/text_import.py
docs/IMPORTACION_LOCAL.md
docs/IMPORTACION_LF_CRLF.md
docs/INSTALACION_WINDOWS.md
docs/INSTALADOR.md
docs/ETAPA2_VALIDACION_FINAL.md
docs/distribution_inventory.json
tests/run_tests.py
tests/test_local_import.py
tests/test_text_import.py
```

El conjunto completo se identifica en [distribution_inventory.json](distribution_inventory.json). Los registros detallados de esta ejecución permanecen en `validation/etapa2_final_20261030/`, ignorado por Git y no publicable.

## Uso después de publicar la corrección

Desde la raíz de una copia actualizada, con Python 3.12 disponible y una carpeta Deploy compatible obtenida legítimamente:

```powershell
.\scripts\instalar.ps1 -NoInteractivo -DeployPath "RUTA_DE_TU_DEPLOY"
.\scripts\verificar.ps1
.\scripts\jugar_automatico.ps1 -Headless
.\scripts\jugar_automatico.ps1
```

`RUTA_DE_TU_DEPLOY` es un parámetro que debe sustituirse por la carpeta real del usuario. La validación realizada utilizó la carpeta original local CRLF, no un Deploy oficial sin adaptaciones. Descargar únicamente GitHub sigue proporcionando 78/104 recursos: hace falta una copia compatible y legítima para completar la instalación. Los permisos de redistribución pendientes no cambiaron. El clon antiguo conserva su importador anterior hasta una actualización expresamente autorizada.

No se ejecutaron `git add`, commit ni push. **Listo técnicamente para revisar/publicar la corrección, con las limitaciones de recursos externos ya documentadas.**
