# RoboPenalty AI

**Dos robots, un penal y decisiones autónomas.** Proyecto académico de Inteligencia Artificial de UADE: una simulación física de penales entre dos humanoides Unitree G1, con un delantero que selecciona tiros y un arquero que observa la pelota y planifica su intercepción.

Esta distribución reúne la versión interactiva **9A**, el catálogo calibrado **8C** y el estadio **7D**. El objetivo es ofrecer una demostración reproducible de percepción, predicción, decisión y aprendizaje estadístico dentro de MuJoCo.

## Cómo instalar y jugar

### Instalación y ejecución

**Necesitás Windows, CPython 3.12 x64 y una copia Deploy adaptada TP07 compatible obtenida legítimamente.** El repositorio solo tiene 78/104 recursos. El Deploy oficial por sí solo no alcanza y los 26 faltantes no se descargan automáticamente.

**1. Descargar.** En [RoboPenalty-AI-UADE](https://github.com/agreboyras/RoboPenalty-AI-UADE), elegir **Code → Download ZIP**, extraerlo y abrir en VS Code la carpeta `RoboPenalty-AI-UADE-main` que contiene `app/` y `scripts/`. Como alternativa, con Git:

```powershell
git clone https://github.com/agreboyras/RoboPenalty-AI-UADE.git
Set-Location -LiteralPath .\RoboPenalty-AI-UADE
```

**2. Preparar la copia externa.** La fuente técnica compatible es [TP07 en la revisión ce4b34d…](https://github.com/agreboyras/TP07-IA-G1-Futbol/tree/ce4b34d1bccfd0420a81bf1688271d86feb8a117), con ocho modificaciones y tres adiciones respecto del [Deploy oficial f60f244…](https://github.com/OpenDriveLab/RoboNaldo_Deploy/tree/f60f24459aaabc3aea9187a2b13f8923049b629c). Su disponibilidad pública no resuelve las condiciones de uso. El equipo debe confirmar una vía autorizada para cada integrante; **si no tenés esa copia legítima, no hay actualmente un paso automático autorizado que complete la instalación**. No hace falta acceder a la computadora del autor ni buscar archivos sueltos: la guía identifica fuente, revisión y el conjunto exacto.

**3. Instalar desde la raíz del proyecto.** Abrir PowerShell en VS Code:

```powershell
py -3.12 --version
.\scripts\instalar.ps1
```

El instalador pide la carpeta Deploy si detecta una terminal interactiva y faltan recursos. Pegar la ruta de la carpeta que contiene directamente `FSM/`, `common/`, `deploy_mujoco/` y `policy/`. Puede estar en cualquier ubicación fuera de RoboPenalty y tener espacios. Si no pregunta, usar `-Interactivo`. ENTER sin carpeta prepara solo Python y los 78 recursos disponibles: termina **PARCIAL**, con el juego bloqueado.

Si `py -3.12` no encuentra Python, instalar CPython 3.12 x64 o indicar el ejecutable que ya tengas instalado, sin asumir ninguna ruta del autor:

```powershell
$pythonEquipo = Read-Host "Ruta completa del ejecutable Python 3.12 x64"
& $pythonEquipo --version
.\scripts\instalar.ps1 -Python $pythonEquipo -Interactivo
```

Con una ruta conocida y sin preguntas (ejemplo de carpeta hermana):

```powershell
.\scripts\instalar.ps1 -NoInteractivo -DeployPath '..\Deploy Compatible'
```

Si PowerShell bloquea los scripts, revisar [preparación de Windows](docs/INSTALACION_WINDOWS.md#2-preparar-windows). El instalador crea `.venv`; no hace falta activarlo. No instala Isaac, SDK de robot ni modelos de voz.

**4. Verificar y jugar.** Solo continuar cuando la instalación indique 104/104 recursos correctos:

```powershell
.\scripts\verificar.ps1
.\scripts\jugar_automatico.ps1
# O bien, cuando haya cerrado la primera tanda:
.\scripts\jugar_dirigido.ps1
```

Abren el visor MuJoCo y ejecutan cinco penales. En modo dirigido, escribir `Iniciar partido`, esperar la solicitud y dar una orden por penal: `Patea al centro`, `Patea a la izquierda` (centro-izquierda), `Patea a la derecha`, `Patea a la derecha abierta` o `Patea a la esquina derecha`. Controles: `mostrar marcador`, `pausar partida`, `reanudar partida`, `salir`. El arquero permanece autónomo. Sin ventana: `jugar_automatico.ps1 -Headless`.

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

La batería actual aprobó **144 tests: los 134 anteriores y diez nuevos de instalación guiada**. La prueba nueva, en una carpeta y entorno creados desde cero, completó tres tandas: automática headless, dirigida por entrada real de consola y automática con visor. Cada una registró 35.000 pasos, 3 goles, 2 atajadas y 0 errados, con igualdad exacta de los estados y trazas comparados frente a 8C. Las órdenes manuales conservaron su historial separado.

Se comprobó también el caso sin Deploy: código 2 y partida bloqueada, y el diálogo real con ENTER vacío o carpeta compatible. Estos resultados pertenecen a esta computadora y no garantizan otra máquina física. Ver [prueba nueva, tiempos y límites](docs/INSTALACION_GUIADA_RESULTADOS.md) y [comparación base](docs/LOCAL_IMPORT_RESULTS.md). Las tandas no se ejecutan automáticamente al correr los tests unitarios.

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
