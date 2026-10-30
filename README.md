# RoboPenalty AI

**Dos robots, un penal y decisiones autónomas.** Proyecto académico de Inteligencia Artificial de UADE: una simulación física de penales entre dos humanoides Unitree G1, con un delantero que selecciona tiros y un arquero que observa la pelota y planifica su intercepción.

Esta distribución reúne la versión interactiva **9A**, el catálogo calibrado **8C** y el estadio **7D**. El objetivo es ofrecer una demostración reproducible de percepción, predicción, decisión y aprendizaje estadístico dentro de MuJoCo.

## Cómo instalar y jugar

### Instalación y ejecución

**Necesitás Windows, Git, CPython 3.12 x64 con el lanzador `py` y una copia TP07 compatible cuyo uso esté legítimamente permitido.** El repositorio RoboPenalty contiene 78/104 recursos. Los 26 restantes están técnicamente disponibles en TP07, pero sus permisos heredados siguen pendientes de aclaración con OpenDriveLab: que TP07 sea público **no concede una licencia** sobre ese material. No se incluyen ni se descargan automáticamente desde el instalador. Ver [THIRD_PARTY.md](THIRD_PARTY.md).

**1. Comprobar requisitos y clonar.** Abrir PowerShell en una carpeta de trabajo nueva. Git se obtiene desde [Git para Windows](https://git-scm.com/download/win) y Python desde [Python para Windows](https://www.python.org/downloads/windows/). Con el acceso y uso de los recursos externos resueltos, ejecutar:

```powershell
git --version
py -3.12 -c "import sys; print(sys.version); assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32"

git -c core.autocrlf=false clone https://github.com/agreboyras/RoboPenalty-AI-UADE.git
git -c core.autocrlf=false clone https://github.com/agreboyras/TP07-IA-G1-Futbol.git
git -C TP07-IA-G1-Futbol checkout --detach ce4b34d1bccfd0420a81bf1688271d86feb8a117
Set-Location -LiteralPath .\RoboPenalty-AI-UADE
```

Los dos repositorios quedan como carpetas hermanas. Se fija el commit TP07 validado para no depender de cambios futuros en `main`. **La raíz de `TP07-IA-G1-Futbol` es el Deploy que se importa**: contiene directamente `FSM/`, `common/`, `deploy_mujoco/` y `policy/`. No hay que buscar una subcarpeta llamada `RoboNaldo_Deploy`, instalar los requirements de TP07 ni ejecutar su programa. El Deploy oficial sin adaptaciones no alcanza.

**2. Instalar y verificar.** Desde la raíz de RoboPenalty:

```powershell
$pythonEquipo = py -3.12 -c "import sys; print(sys.executable)"
.\scripts\instalar.ps1 -Python "$pythonEquipo" -NoInteractivo -DeployPath "..\TP07-IA-G1-Futbol"
if ($LASTEXITCODE -ne 0) { throw "Instalacion incompleta: revisar el diagnostico antes de jugar" }
.\scripts\verificar.ps1
```

Continuar únicamente con **104/104 recursos, inventario y paquetes OK**. El instalador crea `.venv` y no hace falta activarlo. Si solo se descarga RoboPenalty, se puede preparar Python y correr tests, pero sin los 26 recursos el juego queda bloqueado. No se instala Isaac, SDK de robot ni modelos de voz.

La importación admite LF o CRLF únicamente en los textos enumerados si CRLF→LF produce el SHA-256 esperado; copia los bytes canónicos sin modificar TP07. ONNX y NPZ mantienen comprobación estricta. [Detalle de integridad](docs/IMPORTACION_LF_CRLF.md).

Si Python no aparece en `py`, PowerShell bloquea scripts, preferís descargar ZIP o ya tenés Deploy en otra ubicación, seguir las alternativas de la [guía Windows](docs/INSTALACION_WINDOWS.md). No hace falta acceder a carpetas de la computadora del autor.

**3. Jugar cinco penales.** Elegir una modalidad por vez:

```powershell
# Automático con visor: comienza la tanda.
.\scripts\jugar_automatico.ps1

# Dirigido por texto con visor: espera tus órdenes.
.\scripts\jugar_dirigido.ps1

# Automático sin ventana.
.\scripts\jugar_automatico.ps1 -Headless
```

En modo dirigido, escribir `Iniciar partido`, esperar la solicitud y dar una orden por penal: `Patea al centro`, `Patea a la izquierda` (centro-izquierda), `Patea a la derecha`, `Patea a la derecha abierta` o `Patea a la esquina derecha`. Controles: `mostrar marcador`, `pausar partida`, `reanudar partida`, `salir`. El arquero permanece autónomo.

La prueba con clones limpios de ambos repositorios, en la revisión TP07 fijada, completó **104/104 recursos, 170 tests y cinco penales automáticos headless: 3 goles, 2 atajadas, 0 errados y 35.000 pasos**. Esa prueba no repitió el visor ni representa validación en otra computadora física.

**[Guía completa para estudiantes: descarga, recursos, instalación y solución de errores](docs/INSTALACION_WINDOWS.md).** Las fuentes y avisos se conservan en [THIRD_PARTY.md](THIRD_PARTY.md). La voz sigue pendiente de validación y está desactivada.

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

## Detalles de instalación

La [guía Windows](docs/INSTALACION_WINDOWS.md) identifica las revisiones, los 26 archivos pendientes, el modo interactivo y `-NoInteractivo`, las rutas con espacios, el diagnóstico y los códigos de salida. [Importación local](docs/IMPORTACION_LOCAL.md) describe la integridad y la separación entre datos locales y contenido público. No se modifican hashes ni se aceptan sustitutos.

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

La batería actual aprobó **170 tests: los 144 anteriores y 26 nuevos de importación LF/CRLF**. La validación previa de instalación guiada, en una carpeta y entorno creados desde cero, completó tres tandas: automática headless, dirigida por entrada real de consola y automática con visor. Cada una registró 35.000 pasos, 3 goles, 2 atajadas y 0 errados, con igualdad exacta de los estados y trazas comparados frente a 8C. Las órdenes manuales conservaron su historial separado.

Se comprobó también el caso sin Deploy: código 2 y partida bloqueada, y el diálogo real con ENTER vacío o carpeta compatible. Estos resultados pertenecen a esta computadora y no garantizan otra máquina física. Ver [prueba nueva, tiempos y límites](docs/INSTALACION_GUIADA_RESULTADOS.md) y [comparación base](docs/LOCAL_IMPORT_RESULTS.md). Las tandas no se ejecutan automáticamente al correr los tests unitarios.

## Errores comunes y limitaciones

- **Faltan recursos o el hash difiere:** revisar la carpeta elegida con `importar_deploy.ps1 -Inspeccionar`. La copia oficial sola carece de ocho modificaciones y tres adiciones TP07. No editar manifiestos ni sustituir modelos o NPZ parecidos.
- **LF/CRLF:** se admiten únicamente al importar los textos enumerados, si CRLF→LF produce el SHA canónico exacto. Los archivos ya instalados deben conservar sus bytes canónicos; no se normalizan binarios ni se corrigen cambios de contenido. `.gitattributes` preserva los bytes versionados.
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
