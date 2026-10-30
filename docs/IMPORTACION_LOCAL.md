# Ejecutar con una carpeta Deploy local

Este paquete permite importar los 26 recursos requeridos desde una copia adaptada TP07 que el usuario ya haya obtenido legitimamente. No los publica, no concede licencias y no habilita sus descargas pendientes. La copia oficial se reconoce por sus hashes, pero no basta para ejecutar: requiere ocho archivos modificados y tres adicionales. No se incluyen parches derivados; el mecanismo generico de reconstruccion necesita material adaptado autorizado y no puede inventarlo.

## Procedimiento Windows

Desde la carpeta del proyecto, con CPython 3.12 x64 instalado, colocar la copia Deploy fuera del paquete (puede tener cualquier nombre). Ejemplo de estructura: proyecto y `DeployTP07` como carpetas hermanas.

```powershell
# Si Windows bloquea scripts locales: solo esta terminal, no cambia la politica global.
Set-ExecutionPolicy -Scope Process RemoteSigned

# Comprobacion opcional: no copia ni modifica nada.
./scripts/importar_deploy.ps1 -DeployPath ../DeployTP07 -Inspeccionar

# Prepara recursos BSD, importa los 26 archivos exactos y crea un entorno propio.
./scripts/instalar.ps1 -DeployPath ../DeployTP07
./scripts/verificar.ps1

# Visor por defecto; voz desactivada.
./scripts/jugar_dirigido.ps1
./scripts/jugar_automatico.ps1
```

Tambien se puede ejecutar `./scripts/importar_deploy.ps1` sin argumento: solicita la carpeta en consola. Para importar sin instalar paquetes, usar `instalar.ps1 -SoloRecursos -DeployPath ../DeployTP07`; despues ejecutar `instalar.ps1` para preparar Python. Una instalacion ya importada no necesita de nuevo la fuente para jugar o reinstalar paquetes.

La entrada recomendada para estudiantes es ahora `./scripts/instalar.ps1`: pregunta por la carpeta solo si detecta una terminal interactiva y faltan recursos. `-Interactivo` fuerza la pregunta; `-NoInteractivo` la deshabilita para automatizacion. Una ruta explicita con `-DeployPath` evita preguntas. ENTER sin carpeta no autoriza descargas: prepara una instalacion parcial y retorna 2. Ver la guia completa INSTALACION_WINDOWS.md para descargar el proyecto y distinguir la fuente tecnica TP07 de los permisos pendientes.

Modo dirigido: `Iniciar partido`, despues una orden por penal: `Patea a la derecha`, `Patea a la derecha abierta`, `Patea a la esquina derecha`, `Patea a la izquierda` (centro-izquierda) o `Patea al centro`. `Pausar partida`, `Reanudar partida`, `Mostrar marcador`, `Salir`. El arquero permanece autonomo.

## Integridad y fallos

- Se verifican todos los 26 archivos antes de copiar. Se usan exactamente los SHA-256 existentes; tambien se comprueban los otros 78 recursos y el inventario del paquete antes de jugar.
- Diferencias LF/CRLF se informan y rechazan: no se convierten bytes silenciosamente. Obtener la copia exacta adecuada; no editar el manifiesto para hacerla pasar.
- Una carpeta oficial o incompleta no importa nada. Se enumeran todos los faltantes y diferencias. No sustituir NPZ/ONNX por otros parecidos.
- Una interrupcion puede dejar archivos parciales ya terminados; una nueva importacion reutiliza solo los correctos. Los temporales se escriben atomicamente. Un archivo existente diferente se rechaza y no se sobrescribe.
- Los recursos van a `app/RoboNaldo_Deploy/`, en rutas especificamente excluidas de Git. Los avisos cercanos se conservan en `.cache/local_import_notices/` y un registro sin ruta personal en `.cache/local_import.json`. Ambos estan excluidos de Git. No publicar una copia ZIP de la instalacion local como si fuese el paquete publico.
- El diagnostico distingue `execution_ready` (ejecucion local validada) de `distribution_ready` y los permisos pendientes. La importacion no resuelve permisos de redistribucion. El registro local es comprobacion tecnica, no prueba legal.
- Sin carpeta adaptada, instalar prepara Python y los 78 recursos disponibles, pero retorna 2 y bloquea el juego. Un clon de GitHub por si solo sigue sin incluir los 26 recursos.
- La voz sigue pendiente de validacion; no se instalan modelos nuevos ni se activa por defecto.

## Pruebas

```powershell
./.venv/Scripts/python.exe -X utf8 -E -s -B tests/run_tests.py --include-core
```

Las pruebas de importacion usan bytes sinteticos y no requieren red. Los resultados de pruebas fisicas reales se documentan por separado; no se deducen de los tests unitarios.
