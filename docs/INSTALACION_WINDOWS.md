# Instalacion Windows

Requisitos: CPython 3.12 x64, PowerShell y red HTTPS para PyPI. No hace falta Git ni clonar repositorios externos. El instalador no instala Python en el sistema ni descarga modelos de voz.

## Con una copia Deploy adaptada obtenida legitimamente

Desde la raiz del paquete:

```powershell
./scripts/instalar.ps1 -DeployPath ../DeployTP07
./scripts/verificar.ps1
./scripts/jugar_dirigido.ps1
./scripts/jugar_automatico.ps1
```

La carpeta puede tener cualquier nombre o ubicacion fuera de la distribucion. El importador exige los 26 SHA-256 exactos del perfil, conserva avisos y no modifica la fuente. Una copia oficial sola se reconoce pero no basta. Ver [importacion local](IMPORTACION_LOCAL.md) para inspeccion previa, errores LF/CRLF y comandos de juego.

## Sin Deploy adaptado

`./scripts/instalar.ps1` prepara Python y los 78/104 recursos disponibles. Retorna 2 y el juego queda bloqueado. No busca recursos en otras carpetas ni descarga los 26 pendientes. Una descarga de GitHub sola NO es una instalacion completamente autonoma.

## Opciones y errores

- `-SoloRecursos` omite Python; admite tambien `-DeployPath`.
- `verificar.ps1 -ResourcesOnly` comprueba recursos e inventario sin exigir los paquetes.
- `-Python $pythonEquipo` permite indicar un interprete real si no se encuentra CPython 3.12 con py.
- Para ejecutar sin ventana: `jugar_automatico.ps1 -Headless`.
- Si Windows bloquea scripts locales revisados: `Set-ExecutionPolicy -Scope Process RemoteSigned` solo en esa terminal. No cambiar politicas globales; respetar politicas de la organizacion.
- Una diferencia SHA se rechaza sin sobrescribir ni convertir archivos. No editar manifiestos ni sustituir NPZ/ONNX.

El .venv es propio, sin system-site-packages; pip usa el lock core fijado. No se instalan requirements de Deploy. El registro local y los recursos importados quedan fuera de Git; no constituyen una licencia. La voz permanece desactivada y pendiente de validacion.

Si se descargo un ZIP y Windows marco los scripts como procedentes de Internet, RemoteSigned puede seguir rechazando scripts sin firma. Tras revisar los archivos del paquete, se pueden desbloquear exclusivamente sus scripts:

```powershell
Get-ChildItem .\scripts -Filter *.ps1 -File | Unblock-File
Set-ExecutionPolicy -Scope Process RemoteSigned
```

Esto no cambia las politicas globales ni reemplaza las politicas de una organizacion. Si siguen bloqueados por una politica administrada, consultar al administrador.

Pruebas: `./.venv/Scripts/python.exe -X utf8 -E -s -B tests/run_tests.py --include-core`. Resultados de la instalacion local y simulacion: LOCAL_IMPORT_RESULTS.md.
