# RoboPenalty AI

**Dos robots, un penal y decisiones autónomas.** Proyecto académico de Inteligencia Artificial de UADE: una simulación física de penales entre dos humanoides Unitree G1, con un delantero que selecciona tiros y un arquero que observa la pelota y planifica su intercepción.

Esta distribución reúne la versión interactiva **9A**, el catálogo calibrado **8C** y el estadio **7D**. El objetivo es ofrecer una demostración reproducible de percepción, predicción, decisión y aprendizaje estadístico dentro de MuJoCo.

> **Antes de instalar:** descargar este repositorio no basta para jugar. El paquete incluye 78 de los 104 recursos externos del perfil de ejecución. Para completar la instalación hace falta una copia **Deploy adaptada TP07 compatible, obtenida legítimamente**, que aporte los otros 26 archivos exactos. Una copia oficial de RoboNaldo_Deploy por sí sola no alcanza. Los archivos pendientes no se redistribuyen ni se descargan automáticamente.

## Qué incluye

- Dos G1 en un mismo mundo físico: delantero con contacto pie–pelota y arquero autónomo.
- Cinco tiros calibrados: centro, centro-izquierda, intermedio derecho, abierto derecho y esquina derecha.
- Predicción de trayectoria, planificación lateral B y postura defensiva dinámica del arquero.
- Tanda de cinco penales, reinicios entre episodios y evaluación de goles, atajadas y tiros errados.
- Delantero automático basado en utilidad y aprendizaje estadístico entre penales.
- Modo dirigido por texto, con estadísticas manuales separadas del aprendizaje automático.
- Media cancha de distancia física de tiro de 6 m, estadio envolvente, pantalla de marcador, cámaras y visor nativo MuJoCo.
- Pausa, reanudación y cierre seguros; ejecución sin ventana para pruebas.

La voz está integrada como opción experimental, pero **no está validada como funcional** y permanece desactivada por defecto.

## Arquitectura y aporte del equipo

| Capa | Responsabilidad |
|---|---|
| Entrada y coordinación 9A | Interpreta texto, valida estados y selecciona acciones antes del penal |
| Agente delantero | Calcula utilidades y actualiza estadísticas después del resultado |
| Agente arquero | Usa observaciones físicas actuales, predice el cruce y decide su reacción |
| Runtime y evaluación | Ejecuta MuJoCo, controla episodios y registra evidencia física |
| Presentación 7D | Dibuja estadio, marcador y cámaras sobre la simulación existente |
| Portabilidad | Verifica manifiestos, importa recursos locales y comprueba dependencias |

La política motriz **FreeKick/ONNX proviene de RoboNaldo**, no fue entrenada por este equipo. El trabajo propio se concentra en la integración, agentes de decisión, planificación, aprendizaje estadístico, orquestación, evaluación y presentación. El aprendizaje del delantero actualiza estadísticas de selección de acciones; **no reentrena la política motriz**.

En modo dirigido, la orden selecciona un tiro físico existente. No aplica impulsos artificiales ni fija la trayectoria de la pelota. El arquero recibe observaciones físicas, sin acceder a la orden ni al preset del usuario.

```text
app/RoboPenalty/       Runtime, agentes, presentación y portabilidad
app/RoboNaldo_Deploy/  Meshes BSD y estructura; recursos locales adicionales ignorados por Git
app/unitree_mujoco/    Modelo G1, meshes y licencia BSD
scripts/              Instalación, importación, diagnóstico y lanzadores Windows
tests/                Tests de paquete, importación, instalador y componentes
docs/                 Fuentes, integridad, instalación y resultados
```

Se incluyen los módulos transitivos necesarios de fases anteriores, no todo el archivo histórico de desarrollo.

## Instalación en Windows

### 1. Preparar el equipo

- Windows con **CPython 3.12 de 64 bits** y PowerShell.
- Acceso a PyPI para instalar las versiones fijadas en `app/RoboPenalty/requirements-windows.txt`.
- Controlador gráfico compatible con el visor MuJoCo; también se puede ejecutar headless.
- Carpeta Deploy adaptada compatible, obtenida legítimamente. Sus hashes y revisiones de procedencia están documentados en [dependencias](docs/RECURSOS_PENDIENTES.md).

Descargar el ZIP de este repositorio y extraerlo, o clonarlo. Abrir en VS Code la carpeta que contiene este README, `app/` y `scripts/`. Git no es necesario para instalar ni jugar.

Comprobar Python:

```powershell
py -3.12 --version
```

### 2. Importar recursos e instalar

La carpeta Deploy puede tener cualquier nombre y estar en cualquier ubicación fuera de esta distribución. Por ejemplo, si se encuentra en una carpeta hermana llamada `DeployTP07`:

```powershell
# Opcional: inspeccionar primero, sin copiar nada.
.\scripts\importar_deploy.ps1 -DeployPath ..\DeployTP07 -Inspeccionar

# Importar los 26 archivos exactos, crear .venv e instalar paquetes.
.\scripts\instalar.ps1 -DeployPath ..\DeployTP07
```

También se puede usar una ruta elegida en consola:

```powershell
$deploy = Read-Host "Ruta de la carpeta Deploy adaptada"
.\scripts\instalar.ps1 -DeployPath $deploy
```

El instalador conserva avisos, exige SHA-256 exacto y deja los archivos importados fuera de Git. No busca las carpetas del autor ni convierte LF/CRLF. Después de importar correctamente, la carpeta fuente no se necesita para jugar.

**Sin Deploy adaptado**, `instalar.ps1` prepara Python y los 78 recursos disponibles, termina con código 2 y mantiene bloqueada la partida. No existe una opción para ignorar hashes o conceder permisos.

### 3. Verificar

```powershell
.\scripts\verificar.ps1
```

Para jugar deben estar correctos **104/104 recursos**, el inventario del paquete, el registro de importación local y los paquetes Python. El diagnóstico distingue la habilitación técnica local de los permisos pendientes de redistribución.

## Jugar cinco penales

```powershell
# El delantero decide; el arquero actúa autónomamente.
.\scripts\jugar_automatico.ps1

# El usuario selecciona cada tiro por texto; el arquero sigue autónomo.
.\scripts\jugar_dirigido.ps1

# Alternativa sin ventana.
.\scripts\jugar_automatico.ps1 -Headless
```

Los lanzadores usan cinco penales, semilla 2026, distancia `long` y visor por defecto. El modo automático inicia la tanda; en modo dirigido, escribir `Iniciar partido` y esperar la solicitud de tiro.

| Orden de texto | Acción |
|---|---|
| `Patea al centro` | Central |
| `Patea a la izquierda` | Centro-izquierda disponible |
| `Patea a la derecha` | Intermedio derecho |
| `Patea a la derecha abierta` | Abierto derecho |
| `Patea a la esquina derecha` | Esquina derecha |

No hay esquina izquierda validada en este catálogo. El destino final depende del contacto físico, no es una posición garantizada.

Controles: `ayuda`, `estado`, `mostrar marcador`, `pausar partida`, `reanudar partida`, `salir`. Cámaras: `/cam behind`, `/cam overview`, `/cam goal`, `/cam execution`. La pausa se procesa entre pasos físicos. También se puede cerrar la ventana; un penal interrumpido no se puntúa como completado.

Las salidas de partida se crean bajo `app/RoboPenalty/phase9a/results/` y quedan excluidas de Git.

## Pruebas y validación

```powershell
# Tests del paquete, sin dependencias científicas ni descargas.
py -3.12 -X utf8 -E -s -B tests/run_tests.py

# Con el entorno instalado: también los tests de componentes.
.\.venv\Scripts\python.exe -X utf8 -E -s -B tests/run_tests.py --include-core
```

La validación local aislada registró **134 tests aprobados** y tres tandas completas: automática headless, dirigida por texto y dirigida con visor. Cada tanda completó 35.000 pasos, con 3 goles, 2 atajadas y 0 errados. Los estados y las trazas físicas registradas coincidieron exactamente con el baseline 8C para la secuencia comparada; también se comprobó el aislamiento de estadísticas manuales.

Estos resultados corresponden a un entorno nuevo en la computadora de validación, no a una segunda computadora física. Ver [pruebas, tiempos y límites de comparación](docs/LOCAL_IMPORT_RESULTS.md). Las tandas no se ejecutan automáticamente al correr los tests unitarios.

## Errores comunes y limitaciones

- **Faltan recursos o el hash difiere:** revisar la carpeta elegida con `importar_deploy.ps1 -Inspeccionar`. La copia oficial sola carece de ocho modificaciones y tres adiciones TP07. No editar manifiestos ni sustituir modelos o NPZ parecidos.
- **LF/CRLF distintos:** se rechazan expresamente; conseguir los bytes compatibles. `.gitattributes` preserva los bytes incluidos en este repositorio.
- **No se encuentra Python 3.12:** instalar CPython 3.12 x64 o pasar `-Python $pythonEquipo` con un ejecutable real. No usar el entorno de otro proyecto.
- **PowerShell bloquea scripts:** revisar [instalación Windows](docs/INSTALACION_WINDOWS.md); cualquier cambio de política sugerido es solo para esa terminal, sujeto a las políticas del equipo.
- **Fallo de red:** corregir la conexión y repetir la instalación. Solo se reutilizan recursos completos cuyos hashes coinciden; un archivo distinto no se sobrescribe.
- **El visor falla:** comprobar el controlador gráfico y probar `-Headless`. La instalación y el rendimiento en otros equipos todavía requieren validación.
- **Voz:** no se presenta como funcional, no se incluyen modelos Whisper ni se activa durante la instalación estándar.

El escenario es de fútbol robótico a escala adaptada; el arquero tiene guía lateral, no locomoción libre ni saltos. El catálogo es finito y algunas trayectorias son sensibles a condiciones iniciales: la validación nominal no demuestra robustez global.

## Créditos y documentación

Proyecto académico de Inteligencia Artificial, UADE. Referencias externas: [OpenDriveLab/RoboNaldo](https://github.com/OpenDriveLab/RoboNaldo), [RoboNaldo_Deploy](https://github.com/OpenDriveLab/RoboNaldo_Deploy), [Unitree MuJoCo](https://github.com/unitreerobotics/unitree_mujoco) y [Unitree ROS](https://github.com/unitreerobotics/unitree_ros). La adaptación TP07 y las revisiones exactas están identificadas en los manifiestos.

Los recursos Unitree incluidos conservan sus licencias BSD-3-Clause. Los 26 recursos Deploy pendientes no forman parte del contenido publicable. La importación local no concede derechos de uso ni redistribución. Consultar [THIRD_PARTY.md](THIRD_PARTY.md) para procedencia, avisos y límites. El equipo todavía debe acordar una licencia para su código propio; no se aplica una licencia global a los componentes externos.

- [Importación local](docs/IMPORTACION_LOCAL.md)
- [Instalación Windows](docs/INSTALACION_WINDOWS.md)
- [Infraestructura e integridad](docs/INSTALADOR.md)
- [Inventario](docs/INVENTARIO.md)
- [Resultados medidos](docs/LOCAL_IMPORT_RESULTS.md)
