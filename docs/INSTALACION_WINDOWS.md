# Instalación de RoboPenalty AI UADE en Windows

Esta guía parte de una computadora que nunca usó RoboPenalty. No requiere las carpetas del autor, Conda, Isaac Sim, Isaac Lab, PyTorch, ROS, SDK de Unitree ni un robot físico.

**Requisito que no puede resolver el instalador:** además del repositorio público se necesita una copia Deploy adaptada TP07 compatible obtenida legítimamente. El paquete público tiene 78/104 recursos; los 26 restantes no se descargan automáticamente. Sin ellos se pueden instalar paquetes, revisar código y correr tests, pero no jugar. Una carpeta oficial de Deploy sola no alcanza.

## 1. Descargar y abrir la carpeta correcta

Repositorio: [agreboyras/RoboPenalty-AI-UADE](https://github.com/agreboyras/RoboPenalty-AI-UADE).

**Sin Git:** abrir el enlace, pulsar **Code → Download ZIP**, extraer todo el ZIP y abrir en VS Code la carpeta `RoboPenalty-AI-UADE-main`. No ejecutar archivos dentro de la vista del ZIP. En esa carpeta deben verse `README.md`, `scripts/`, `app/` y `tests/`. Abrir **Terminal → New Terminal** y seleccionar PowerShell.

**Con Git (procedimiento recomendado y validado)**, instalar [Git para Windows](https://git-scm.com/download/win) y ejecutar desde una carpeta de trabajo nueva. El clonado de TP07 queda sujeto a las condiciones de uso explicadas en el paso 3:

```powershell
git --version
git -c core.autocrlf=false clone https://github.com/agreboyras/RoboPenalty-AI-UADE.git
git -c core.autocrlf=false clone https://github.com/agreboyras/TP07-IA-G1-Futbol.git
git -C TP07-IA-G1-Futbol checkout --detach ce4b34d1bccfd0420a81bf1688271d86feb8a117
Set-Location -LiteralPath .\RoboPenalty-AI-UADE
```

Quedan dos carpetas hermanas. `checkout --detach` fija la revisión validada de TP07; no hay que editar sus archivos ni actualizarlo a otra revisión para esta instalación. No se necesita crear una rama. Si descargaste RoboPenalty como ZIP, podés usar la misma disposición con el TP07 de la revisión fijada, según el paso 3.

Los comandos siguientes se ejecutan desde la raíz del proyecto. La carpeta puede tener espacios; usar comillas al escribir rutas.

## 2. Preparar Windows

Instalar **CPython 3.12 x64** desde [Python para Windows](https://www.python.org/downloads/windows/), incluyendo el lanzador `py`. Cerrar y abrir la terminal después de instalar.

```powershell
py -3.12 -c "import sys; print(sys.version); assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32"
$PSVersionTable.PSVersion
```

Se requiere Python 3.12 de 64 bits y PowerShell 5.1 o posterior. El instalador los comprueba. Para el visor se necesita un controlador gráfico compatible con MuJoCo; sin ventana se puede usar `-Headless`. Para instalar paquetes hace falta acceso HTTPS a PyPI.

Si Python 3.12 está instalado pero no registrado en `py`, indicar su ejecutable explícitamente. Usar esta variante en lugar del primer comando de instalación; los scripts posteriores detectarán el `.venv` creado:

```powershell
$pythonEquipo = Read-Host "Ruta completa del ejecutable Python 3.12 x64"
& $pythonEquipo --version
.\scripts\instalar.ps1 -Python $pythonEquipo -Interactivo
```

No seleccionar el Python de otro proyecto. La prueba limpia utilizó esta opción porque el lanzador `py` de la sesión no tenía CPython registrado. El instalador no instala Python globalmente.

Si Windows bloquea scripts locales revisados:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
```

Si el ZIP descargado dejó los scripts marcados como provenientes de Internet, revisar los archivos del proyecto y desbloquear únicamente sus scripts:

```powershell
Get-ChildItem .\scripts -Filter *.ps1 -File | Unblock-File
```

No cambiar políticas globales ni intentar eludir políticas de una organización; consultar al administrador si una política administrada los bloquea.

## 3. Conseguir y preparar Deploy compatible

### Qué fuente corresponde a cada parte

| Grupo | Fuente/revisión | Estado del instalador |
|---|---|---|
| 38 recursos Unitree MuJoCo | `unitreerobotics/unitree_mujoco`, `1eb6642e3f3fdfb7fb13a9794fd6a2dd93ea0e7d` | Incluidos con BSD-3-Clause y SHA verificado |
| 35 meshes Unitree ROS y aviso | `unitreerobotics/unitree_ros`, `38a9b00ecbff0b70e85a7627eb9c65db9a2341f7` | Incluidos; descargador autorizado puede reponer sus destinos verificados |
| Cinco archivos vacíos de estructura | Generados localmente, SHA de cero bytes | Generación habilitada |
| 15 originales Deploy (13 fuentes/configuraciones, ONNX y NPZ) | `OpenDriveLab/RoboNaldo_Deploy`, `f60f24459aaabc3aea9187a2b13f8923049b629c` | Fuentes identificadas; descarga no habilitada por condiciones pendientes |
| Ocho modificaciones y tres adiciones TP07 | `agreboyras/TP07-IA-G1-Futbol`, `ce4b34d1bccfd0420a81bf1688271d86feb8a117` | No están en la base oficial; importación local exacta, sin parches redistribuidos |

Referencias verificadas: [Deploy oficial fijado](https://github.com/OpenDriveLab/RoboNaldo_Deploy/tree/f60f24459aaabc3aea9187a2b13f8923049b629c), [TP07 fijado](https://github.com/agreboyras/TP07-IA-G1-Futbol/tree/ce4b34d1bccfd0420a81bf1688271d86feb8a117) y [quickstart original](https://github.com/OpenDriveLab/RoboNaldo/blob/main/docs/quickstart.md). El quickstart original describe entrenamiento y otro entorno; **no seguir sus instrucciones de Isaac/Conda para instalar esta aplicación**.

Un clon limpio obtenido directamente de GitHub en la revisión TP07 fijada contiene los **26 archivos SHA-256 exactos**, incluidos ONNX y NPZ. Se validó una instalación nueva desde ambos repositorios: 104/104 recursos, 170 tests y cinco penales automáticos headless, con 3 goles, 2 atajadas, 0 errados y 35.000 pasos. La rama `main` de TP07 apuntaba a ese mismo commit al comprobarla el 30/10/2026; se fija el commit porque puede cambiar. Eso no concede derechos de uso o redistribución. Los responsables del equipo deben confirmar las condiciones aplicables y una vía autorizada para cada integrante. No se habilitó un descargador de esos archivos ni se recomienda reenviar un ZIP de recursos sin permiso.

**Si ya tenés autorización y acceso aplicables**, la copia compatible corresponde exactamente a esa revisión TP07. Para evitar depender de `main` y de conversiones CRLF, la [descarga ZIP de la revisión fijada](https://github.com/agreboyras/TP07-IA-G1-Futbol/archive/ce4b34d1bccfd0420a81bf1688271d86feb8a117.zip) es una referencia técnica; su uso queda sujeto a aquellas condiciones. Extraer la carpeta fuera de RoboPenalty. No hace falta instalar requirements de TP07 ni ejecutar su programa.

Si todavía **no tenés una copia legítima compatible**, no existe en este paquete un paso autorizado que complete automáticamente esos recursos. Contactar a los responsables del proyecto para resolver acceso/condiciones con los titulares y coordinar la entrega por una vía permitida. Mientras tanto se puede preparar el entorno y estudiar/probar los componentes. Para una demostración inmediata puede usarse una instalación que ya disponga legítimamente de los recursos, sin redistribuirlos.

### Diferencias TP07 que no aporta el Deploy oficial

Ocho archivos modificados:

- `common/logger.py`
- `common/utils.py`
- `deploy_mujoco/config/mujoco_freekick.yaml`
- `deploy_mujoco/deploy_mujoco.py`
- `g1_description/scene_with_ball.xml`
- `policy/fixedpose/FixedPose.py`
- `policy/robonaldo/FreeKick.py`
- `policy/robonaldo/config/freekick.yaml`

Tres añadidos:

- `deploy_mujoco/celebration_coordinator.py`
- `policy/celebration/Celebration.py`
- `policy/celebration/__init__.py`

Se necesitan por imports/recursos transitivos del runtime; no significa que se carguen políticas de festejo durante la tanda. El ONNX requerido es `policy/robonaldo/model/policy-obs-aic.onnx`; el NPZ es `policy/robonaldo/model/freekick_motion.npz`. No sustituirlo por `motions/right_kick.npz` del entrenamiento. El detalle de los 26 archivos y SHA-256 está en `docs/pending_resources.json` y `app/RoboPenalty/portability/external_sources.json`.

### Cómo identificar la carpeta

Debe contener directamente `FSM/`, `common/`, `deploy_mujoco/`, `g1_description/` y `policy/`. Seleccionar esa carpeta, no su padre ni el archivo ZIP. **En el procedimiento con Git del paso 1, seleccionar la raíz de `TP07-IA-G1-Futbol`**, no una subcarpeta `RoboNaldo_Deploy`. Aunque el repositorio se llame TP07, su raíz ya es el árbol Deploy. No ejecutar su programa ni instalar sus requirements. Si usás otra copia compatible, la carpeta puede tener otro nombre.

```powershell
.\scripts\importar_deploy.ps1 -DeployPath '..\TP07-IA-G1-Futbol' -Inspeccionar
```

Una copia adaptada válida muestra `tp07-compatible`, `26/26 recursos compatibles` y cuántos textos requieren CRLF→LF. Para los 24 textos enumerados en el manifiesto, esa única transformación debe dar exactamente el SHA-256 canónico; se realiza en la copia de destino, nunca en el origen. ONNX y NPZ mantienen comparación estricta de sus bytes. Una copia oficial puede mostrar `official-compatible`, pero **se rechaza para ejecutar**; no se genera una adaptación ficticia. La validación es por SHA-256, no por nombre de carpeta.

## 4. Instalar

### Instalación recomendada con los dos clones

Desde la raíz RoboPenalty, usando la carpeta hermana TP07 del paso 1:

```powershell
$pythonEquipo = py -3.12 -c "import sys; print(sys.executable)"
.\scripts\instalar.ps1 -Python "$pythonEquipo" -NoInteractivo -DeployPath "..\TP07-IA-G1-Futbol"
if ($LASTEXITCODE -ne 0) { throw "Instalacion incompleta: revisar el diagnostico antes de jugar" }
.\scripts\verificar.ps1
```

El último comando debe indicar 104/104 y paquetes OK antes de pasar al juego. Si Python no está registrado en `py`, usar su ejecutable real según el paso 2. No hace falta mover ni renombrar TP07.

### Alternativa interactiva para otra carpeta compatible

```powershell
.\scripts\instalar.ps1
```

En una terminal interactiva, si faltan recursos, pregunta por la carpeta Deploy. Pegar la ruta; se aceptan espacios y comillas exteriores. No modifica la fuente. Si no se tiene la copia compatible, pulsar ENTER: prepara solo los recursos disponibles y Python, termina **PARCIAL (código 2)** y bloquea el juego.

Si el host no detecta una terminal interactiva, se puede forzar explícitamente la pregunta:

```powershell
.\scripts\instalar.ps1 -Interactivo
```

Sin Deploy y sin preguntas:

```powershell
.\scripts\instalar.ps1 -NoInteractivo
```

No combinar `-Interactivo` y `-NoInteractivo`. Una instalación ya importada no vuelve a preguntar por la fuente. `-SoloRecursos` omite la creación del entorno y pip; no comprueba que Python científico esté listo para jugar.

El instalador crea `.venv` propio e instala versiones fijadas desde PyPI. **No hace falta activar el entorno** ni ejecutar `Activate.ps1`. Exige todos los hashes; los 26 archivos importados, sus avisos y el registro local quedan fuera de Git. No se descargan modelos Whisper.

Mensajes esperados:

- `Instalacion local completa: 104/104 recursos exactos`: instalación técnica local completa, código 0.
- `INSTALACION PARCIAL: 78/104 recursos; NO se puede jugar`: Python preparado pero falta Deploy, código 2.
- Fallo de red, paquetes, versión o integridad: error; no se habilita el juego ni se disimula como éxito.

No hay una duración universal prometida: la instalación descarga paquetes y depende de la conexión. La prueba con clones públicos del 30/10/2026 tardó 153,58 s en instalar; la sesión automática headless duró 55,60 s reales para 70 s simulados. Son mediciones de esta computadora, no una estimación garantizada para otros equipos.

## 5. Verificar antes de jugar

```powershell
.\scripts\verificar.ps1
```

Debe mostrar ejecución local APTA, recursos `104/104`, inventario y paquetes OK. Que los permisos de **redistribución** sigan pendientes no es un error de integridad de una copia local válida ni una autorización implícita para publicarla.

Para inspeccionar únicamente recursos, sin exigir paquetes:

```powershell
.\scripts\verificar.ps1 -ResourcesOnly
```

El verificador enumera faltantes y diferencias; no modifica los archivos. La tolerancia CRLF→LF existe únicamente en la importación de textos enumerados; después, los 104 archivos instalados deben coincidir byte a byte con el perfil. Ante otra diferencia, no editar hashes ni borrar calibraciones: comprobar la revisión y conseguir los bytes correctos. Ante una copia pública dañada, conservarla y extraer una copia íntegra en una carpeta nueva.

## 6. Ejecutar cinco penales

```powershell
# Automático: inicia la tanda y el delantero elige sus acciones.
.\scripts\jugar_automatico.ps1

# Dirigido por texto: espera la orden de inicio y una selección por penal.
.\scripts\jugar_dirigido.ps1
```

Ejecutar una modalidad por vez. Ambos abren el visor, usan semilla 2026, distancia `long`, cinco penales y voz desactivada. Deben verse los dos G1, pelota, arco, estadio y marcador. El arquero siempre es autónomo.

En modo dirigido:

1. Escribir `Iniciar partido`.
2. Esperar el mensaje de selección.
3. Escribir una orden: `Patea a la derecha`, `Patea a la derecha abierta`, `Patea a la esquina derecha`, `Patea a la izquierda` (centro-izquierda) o `Patea al centro`.
4. Esperar el resultado y repetir hasta completar cinco penales.

Controles: `mostrar marcador`, `estado`, `ayuda`, `pausar partida`, `reanudar partida`, `salir`. Cámaras: `/cam behind`, `/cam overview`, `/cam goal`, `/cam execution`. La pausa se ejecuta entre pasos físicos. Cerrar el visor también termina de forma controlada; un penal interrumpido no se contabiliza como completo.

Sin ventana:

```powershell
.\scripts\jugar_automatico.ps1 -Headless
```

La referencia automática registró 3 goles, 2 atajadas, 0 errados y 35.000 pasos. No exigir ese marcador a una secuencia manual distinta ni fabricar un resultado: se evalúa la física. Las salidas quedan en `app/RoboPenalty/phase9a/results/`, excluidas de Git.

## 7. Solucionar problemas

| Problema | Acción comprobable |
|---|---|
| No aparece Python 3.12 | Comprobar `py -3.12 --version`; instalar CPython 3.12 x64. Si existe un ejecutable sin lanzador, usar `-Python $pythonEquipo` con su ruta real entre comillas. |
| Scripts bloqueados | Revisar los archivos y seguir el paso 2; no cambiar políticas globales. |
| Falló pip | Leer el error de paquetes/red, comprobar conexión HTTPS a PyPI y repetir `instalar.ps1 -NoInteractivo`. El entorno queda separado de otros proyectos. No instalar a ciegas requirements externos ni quitar pines. |
| Entorno interrumpido sin Python ejecutable | Conservar la carpeta y usar una extracción nueva; no reutilizar un entorno ajeno ni borrar datos históricos. |
| Deploy oficial/incompatible | Ejecutar `importar_deploy.ps1 -Inspeccionar`; se requieren los 26 archivos TP07 exactos, no solo el ONNX. |
| Recursos faltantes | Revisar la lista de `verificar.ps1`; conseguir legítimamente la copia compatible e indicar su carpeta. |
| Error SHA / LF-CRLF | Usar esta revisión del importador: acepta solo CRLF→LF en textos enumerados con SHA canónico exacto. No admite espacios/BOM/codificación distintos ni binarios alterados; conseguir una fuente compatible. No editar hashes ni convertir archivos instalados. |
| Visor no abre | Revisar el error gráfico/controlador y probar `jugar_automatico.ps1 -Headless`. No se promete solucionar un fallo DLL o gráfico sin ese error concreto. |
| Ruta con espacios | Usar comillas: `-DeployPath '..\Deploy Compatible'`. El importador usa rutas literales, no comodines. |
| Descarga incompleta/conexión | Corregir conexión y repetir; solo se reutilizan archivos completos con SHA correcto. Los temporales no cuentan como recursos válidos. |
| Voz/micrófono | Esta guía usa texto; la voz sigue pendiente y no forma parte de la instalación estándar. |

## Tests y evidencias

```powershell
# Tests sin paquetes científicos.
py -3.12 -X utf8 -E -s -B tests/run_tests.py

# Con paquetes instalados: añade tests de componentes.
.\.venv\Scripts\python.exe -X utf8 -E -s -B tests/run_tests.py --include-core
```

La batería incluye 170 tests: los 144 previos y 26 de importación LF/CRLF. Ver IMPORTACION_LF_CRLF.md para esa etapa. La prueba de carpeta nueva y las tandas realmente ejecutadas se detallan en `INSTALACION_GUIADA_RESULTADOS.md`. No equivale a validar una segunda computadora física. Atribuciones y condiciones: [THIRD_PARTY.md](../THIRD_PARTY.md).
