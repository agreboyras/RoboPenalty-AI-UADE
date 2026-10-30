# Infraestructura automatica y sus limites

## Fuentes congeladas

portability/external_sources.json contiene 66 recursos mas un aviso. Por recurso: destino permitido, categoria, autorizacion, fuente HTTPS, repositorio, revision de 40 caracteres, SHA-256 y tamano. El perfil runtime de 104 y el historico de 209 siguen intactos. distribution_profile.json ancla sus hashes. La integridad del paquete cubre el nuevo manifiesto y el codigo del descargador.

35 meshes y su aviso provienen de unitreerobotics/unitree_ros 38a9b00ecbff0b70e85a7627eb9c65db9a2341f7. Cinco archivos vacios son generables. Quince originales no vacios, ocho modificados y tres anadidos permanecen pendientes: 26 pasos, incluyendo ONNX y NPZ. Nunca se usa main para instalar.

## HTTPS y escrituras

Solo se acepta la URL raw.githubusercontent.com construida exactamente con uno de los pares repositorio/revision revisados. Se rechazan HTTP, otros hosts, redirecciones, consultas y rutas fuera del destino. TLS usa la comprobacion estandar; no se desactiva. Tamano y SHA-256 se verifican en memoria, luego en un archivo temporal hermano y finalmente se renombra atomicamente. Las descargas siguen siendo de bytes exactos: no se normalizan finales de linea ni binarios. La unica excepcion de entrada esta separada en la importacion local de textos expresamente enumerados, descrita en IMPORTACION_LF_CRLF.md.

Reintentos acotados para fallos de red/respuestas incompletas. Hash incorrecto se rechaza. Un destino existente solo se reutiliza si coincide; no se sobrescribe un archivo diferente. Un bloqueo del SO serializa instaladores en la misma carpeta y se libera al cerrar o morir el proceso. La reanudacion es POR ARCHIVO, sin HTTP Range. Un .part huerfano nunca se acepta como recurso ni se versiona; no se eliminan archivos ajenos.

No hay Git, zipball completo, token ni clonacion en el instalador. La carpeta .cache, entornos, pruebas limpias y descargas pendientes quedan excluidos. Los 37 JSON indispensables no estan ignorados.

## Reconstruccion TP07

Los ocho pasos registran SHA de entrada oficial y SHA final del perfil. reconstruction.py implementa una receta efimera de copiar rangos e insertar bytes, aplicada contra la base verificada, comprobando la salida completa. NO se distribuye ninguna receta con contenido de Deploy.

Limitacion explicita: la receta se construiria en memoria a partir de la base oficial y el archivo TP07 final, ambos obtenidos de revisiones fijas y verificados. Por tanto, requiere acceso autorizado a ambos; no es un parche autonomo guardado ni una reimplementacion propia de FreeKick. Las tres adiciones TP07 tambien son pasos pendientes. Los tests del motor usan unicamente datos sinteticos propios. No existe --allow-pending.

## Codigos de salida

install_resources: 0 todos los pasos de descarga resueltos, 1 fallo tecnico, 2 pasos pendientes. instalar.ps1: 0 ejecucion local verificada (tambien por importacion), 1 fallo tecnico, 2 instalacion parcial. verificar.ps1: 0 ejecucion local verificada; 1 faltantes, diferencias o registro/paquetes invalidos. Enumera todos los recursos incorrectos. Los juegos verifican antes de cargar el runtime. -SoloRecursos prepara archivos sin crear entorno ni usar pip. Por defecto el instalador tambien prepara .venv y paquetes core aunque queden pasos bloqueados, sin habilitar la simulacion.

La instalacion completa, tandas y visor siguen pendientes hasta poder ejecutar los 26 pasos de forma autorizada. No se confunden pruebas de infraestructura con equivalencia fisica.

## Importacion local independiente

local_import.py acepta una carpeta seleccionada explicitamente, compara los 26 hashes pendientes y reconoce TP07 compatible u oficial compatible. Una copia oficial requiere 8 modificaciones y 3 adiciones que no se distribuyen como parches. La copia TP07 exacta se importa atomicamente por archivo, con bloqueo compartido, avisos y registro bajo .cache. Los 104 recursos, inventario y paquetes deben pasar para execution_ready. distribution_ready permanece falso mientras falten permisos de redistribucion; la descarga no cambia su politica. Ver IMPORTACION_LOCAL.md.

## Entrada guiada para estudiantes

instalar.ps1 comprueba Windows, Python 3.12 x64 y PowerShell >=5.1. Usa la salida JSON del descargador para mostrar un resumen legible, comprueba el inventario y pide una carpeta cuando faltan recursos y la consola es interactiva. -Interactivo fuerza esa entrada; -NoInteractivo conserva el flujo sin preguntas para tests/automatizacion. No se combinan. Una ruta -DeployPath explicita tiene prioridad y una importacion completa evita nuevas preguntas.

_install_input.ps1 separa deteccion de interactividad, seleccion y comprobacion estricta de los 26 faltantes esperados; no contiene recursos externos ni modifica controles fisicos. Los errores SHA, duplicados o faltantes ajenos no se presentan como instalacion parcial aceptable. El diagnostico imprime N/104; la preparacion parcial no habilita lanzadores. El lock, hashes y avisos existentes permanecen intactos.
