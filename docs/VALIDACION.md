# Estado mas reciente

La via de importacion local ya fue validada con tandas completas. Ver [resultados actuales](LOCAL_IMPORT_RESULTS.md) y LOCAL_IMPORT_RESULTS.json. El informe siguiente conserva la preparacion previa de 78/104: sus limitaciones de ejecucion corresponden a un paquete SIN importar Deploy, y no al ensayo local posterior de 104/104.

# Validacion tecnica del instalador — 2026-10-30

## Resultado y alcance

Estado: instalacion PARCIAL verificada; partida NO habilitada. 78 de 104 recursos runtime correctos, 26 pasos pendientes y licencia ROS adicional conservada. No se ejecutaron tandas, comparacion fisica nueva con 8C ni visor, porque siguen faltando recursos esenciales con condiciones pendientes. La voz no se probo.

## Entorno limpio

Se preparo una copia aislada de los archivos publicables, sin .venv, cache ni archivos de los proyectos de referencia. Se omitieron deliberadamente los 35 meshes ROS, su licencia y los cinco vacios para comprobar su recuperacion. instalar.ps1 obtuvo esos recursos desde HTTPS fijado y creo un entorno propio CPython 3.12.14, include-system-site-packages=false. El unico interprete reutilizado fue CPython base/stdlib; no el .venv original ni sus paquetes.

El instalador instalo desde PyPI los 19 paquetes core fijados, y termino con codigo 2 esperado por los 26 pendientes. Tiempo total medido: 224.088 s, incluyendo HTTPS, creacion de venv, pip y comprobaciones; no es tiempo de simulacion ni renderizado. Numpy, MuJoCo y ONNX Runtime importan desde el nuevo venv; user-site esta deshabilitado y PYTHONPATH ignorado.

Se repitio la preparacion con conexiones de red prohibidas en la prueba: 41 archivos correctos reutilizados, 26 bloqueados, ningun error. La reanudacion se basa en hashes completos por archivo, no en aceptar .part. No se descargaron fuentes pendientes.

## Pruebas automatizadas y funcionales

- 18 tests de paquete: SHA de 37 calibraciones, manifiestos historicos, 38 recursos Unitree previos, conjunto parcial de Deploy, fuentes/permisos y ausencia de artefactos no autorizados.
- 28 tests del instalador: HTTPS y URL fija/permitida, rutas, limites de tamano, rechazo de hash, respuesta incompleta, reintentos, redirecciones, escritura atomica fallida, archivo previo preservado, .part huerfano, reanudacion de una instalacion de varios archivos interrumpida, bloqueo de permisos ANTES de red, manifiesto y reconstruccion con datos sinteticos propios.
- 70 tests de componentes: predictor/agente 25, evaluador 6, utilidad 23, parser/control 12 y seleccion 4. No inicializan una partida fisica.
- El contenido derivado de TP07 NO se usa como fixture ni parche distribuido. Ocho reconstrucciones tienen hashes base/final congelados; su motor esta probado con datos propios. Para una reconstruccion real se requieren ambos archivos externos verificados y permisos revisados; permanece deshabilitada.
- Los siete scripts PowerShell pasan sintaxis. Windows PowerShell 5.1 se ejecuto con RemoteSigned SOLO en el proceso hijo, sin cambiar configuracion global.
- Se probo una diferencia deliberada entre script e inventario en la copia de prueba: el instalador rechazo con codigo 1, sin ocultar el error como parcial aceptable. Despues se actualizo el inventario de la copia revisada.

Ver INSTALLER_RESULTS.json y logs locales bajo validation para los resultados. Los logs crudos contienen rutas del entorno y NO pertenecen al paquete publicable. script_checks.json conserva exclusivamente evidencia historica de la preparacion anterior, no el estado actual.

La bateria final conjunta paso con 116 tests en siete suites: 18 + 28 + 25 + 6 + 23 + 12 + 4. La repeticion de instalar.ps1 devolvio 2, verificar.ps1 devolvio 1 con inventario correcto y 26 faltantes, y ambos juegos rechazaron con su guardia esperada sin producir resultados.

## Git, privacidad y conservacion

Se comprobaron exclusiones con Git en modo solo lectura y sin indice, sin crear repositorio: los 26 destinos pendientes y las carpetas privadas quedan ignorados; los 41 recursos autorizados/generados y las 37 calibraciones permanecen visibles. No se hizo git init, commit, push ni registro de worktree.

El escaneo del conjunto publicable no encontro rutas personales absolutas, patrones de credenciales, dispositivos personales ni recursos pendientes presentes. Los archivos locales validation/.cache/.venv no se incluyen. El escaneo por patrones no demuestra ausencia absoluta de datos privados.

Las 272 fuentes publicables originales y 280 de la copia de portabilidad conservan sus huellas agregadas; los 15 ZIP conservan sus hashes. No se edito fisica, agentes, catalogo, pesos, modelos originales, postura, planificador o calibraciones. La igualdad de bytes no se presenta como una nueva equivalencia fisica ejecutada.

## Pendiente para entregar como funcional

Resolver condiciones aplicables de los 26 pasos, habilitarlos mediante cambio revisado de politica (no bandera de aceptacion), ejecutar reconstruccion/verificacion de archivos reales, tandas automatica/dirigida, comparacion 8C y visor. La infraestructura actual puede desarrollarse/probarse sin esperar esa parte, pero NO declara completo el producto.

El primer intento de descarga desde el sandbox encontro un fallo de DNS y lo informo como error; la ejecucion con acceso de red autorizado completo los recursos BSD. No se deshabilito TLS ni integridad para resolverlo.
