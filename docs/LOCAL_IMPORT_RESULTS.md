# Importacion local: resultados del 30/10/2026

Se implemento una via local para completar recursos exactos ya obtenidos legitimamente. No habilita descargas pendientes ni incorpora Deploy al conjunto publicable. Con solo el paquete publico hay 78/104; tras importar la copia TP07 verificada hay 104/104. La copia oficial fue reconocida con 15 archivos compartidos, ocho bases y tres adiciones ausentes; no se importo ni parcheo automaticamente.

## Validacion aislada real

Se copio exclusivamente el inventario publico a una carpeta nueva bajo validation, se creo un .venv nuevo sin paquetes del sistema y se instalo el lock desde PyPI. La fuente TP07 fue seleccionada explicitamente; el juego no usa su carpeta despues de copiar. Durante las tres tandas un audit hook de Python rechazo accesos a los proyectos originales y a la copia de portabilidad. La comparacion posterior solo leyo JSON del baseline 8C.

| Prueba | Pasos | Resultado | Tiempo de sesion | Proceso completo | Comparacion 8C |
|---|---:|---|---:|---:|---|
| Automatica headless | 35.000 | 3 goles, 2 atajadas, 0 errados | 64,39 s | 70,15 s | Exacta |
| Dirigida por fixture de texto | 35.000 | 3 goles, 2 atajadas, 0 errados | 64,11 s | 70,82 s | Exacta |
| Dirigida con visor y capturas | 35.000 | 3 goles, 2 atajadas, 0 errados | 128,22 s | 133,02 s | Exacta |

Cada tanda simulo 70 segundos. Secuencia: right_inter_m080, right_open_m100, right_corner_m140, left_near_b060, center. Clasificaciones: GOAL, GOAL, GOAL, SAVE, SAVE. Este es el baseline registrado de 8C utilizado, no otra referencia narrativa 4-1.

Cero diferencias en los estados iniciales, trazas de pelota, contactos, decisiones, postura, retorno, monitor y estado completo final de integracion registrados. Comparacion exacta de JSON numerico, sin tolerancias nuevas. Se excluyen tiempos reales, rutas/identificadores de proceso y cantidad de recursos verificados (perfil 104 frente al historico 209). No se afirma una traza de cada variable no registrada en cada paso.

Los cinco tiros tuvieron contacto pie-pelota; no hubo caidas del delantero ni fallos del runtime; los monitores del arquero coincidieron exactamente con el baseline aprobado. El aprendizaje automatico coincidio con 8C; los tiros dirigidos dejaron cinco entradas manuales sin historial de aprendizaje automatico.

El fixture dirigido comprueba inicio, rechazo de direccion ambigua y esquina izquierda no disponible, rechazo durante tiro, pausa y reanudacion, consulta de estado y cambios de camara. La pausa con visor mantuvo el estado completo y t=2 s. El visor uso el mismo mundo fisico, registro 2.551 sincronizaciones/guardias y cerro su hilo correctamente. Las capturas reales y logs estan en validation (excluidos de Git). Los tiempos con visor incluyen pacing, pausas y capturas: NO son FPS ni costo aislado de renderizado.

## Tests e integridad

134 tests: 18 de paquete, 18 de importacion, 28 del instalador y 70 de componentes historicos. Cubren reconocimiento de carpetas, rechazo de CRLF/diferencias, todas las entradas faltantes, ausencia de red, avisos conservados byte a byte, fuente intacta, reanudacion, destino distinto no sobrescrito, registro corrupto o manipulado, bloqueo si falta cualquier recurso e independencia entre ejecucion local y redistribucion. Sintaxis PowerShell comprobada.

El inventario publicable conserva los perfiles 104/209 y los 37 archivos de calibracion. Los 26 recursos importables, cache, resultados de juego, entorno y validacion estan excluidos de Git. No se incluyen parches ni modelos Deploy. Escaneo de patrones sin hallazgos de rutas personales, credenciales o dispositivos; no es una garantia absoluta de ausencia de secretos. No se inicializo Git ni se publicaron cambios.

La primera creacion de venv encontro un bloqueo del sandbox en el temporal de ensurepip; se completo con permiso fuera del sandbox. PyPI tambien requirio acceso de red autorizado tras fallar DNS en el sandbox. No se debilitaron hashes, TLS ni dependencias. La instalacion reanudada termino con codigo 0.

## Limites

La prueba usa un entorno limpio en esta computadora Windows, no otra computadora fisica. Hace falta que cada integrante consiga legitimamente una copia TP07 compatible; la oficial sola no alcanza y no se distribuyen los parches derivados. Un clon sin ella permite instalar lo disponible y ejecutar tests, pero bloquea la simulacion. La voz sigue pendiente y desactivada. Ver IMPORTACION_LOCAL.md para comandos.
