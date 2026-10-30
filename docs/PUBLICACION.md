# Auditoría final de publicación pública

Fecha: 30 de octubre de 2026. Veredicto: **LISTO CON LIMITACIONES** para publicar el conjunto revisado de código, documentación y recursos BSD. No es una distribución autónoma que permita jugar con solo descargar GitHub.

## Alcance y selección

Se recorrieron todas las carpetas, incluidos archivos ocultos, entornos y resultados locales. La selección se calculó con las reglas reales de `.gitignore` mediante `git check-ignore --no-index`, sin crear un repositorio ni escribir un índice. Se desactivaron exclusiones globales para no depender de la configuración personal; el archivo `info/exclude` de la metadata utilizada solo contenía comentarios.

El inventario exacto publicable, con rutas relativas y SHA-256, es `distribution_inventory.json`. El inventario se excluye a sí mismo para evitar una referencia circular; su finalidad es detectar cambios accidentales, no proporcionar una firma autenticada. Las listas completas de archivos admitidos y excluidos y el detalle del escaneo están en `validation/publication_audit/`, solo en la computadora de auditoría y fuera de Git.

| Clase | Qué se publica |
|---|---|
| A: código propio de ejecución | Módulos transitivos de `app/RoboPenalty`, adaptadores, presentación, portabilidad y scripts PowerShell |
| B: recursos y configuración | Catálogo 8C, 37 calibraciones, perfiles 104/209, fuentes fijadas, requisitos Python y cinco archivos vacíos de estructura |
| C: pruebas y documentación | README, THIRD_PARTY, documentación, metadatos de validación sin datos personales y tests con datos sintéticos/componentes |
| D: terceros redistribuibles | 71 meshes Unitree, un XML G1 y dos avisos/licencias BSD-3-Clause completos |
| E: no publicable | Código, XML, ONNX, NPZ y material adaptado de Deploy con permisos de redistribución pendientes; solo copias locales ignoradas |
| F: no publicable | Entornos, caches, copias aisladas, logs, capturas, grabaciones y resultados de ejecución generados |

Los módulos de fases anteriores se conservan porque la presentación/runtime los importan transitivamente o porque los tests de componentes los necesitan. Los 37 JSON son entradas de calibración, no resultados descartables; no se excluye globalmente toda carpeta llamada `results`.

## Exclusiones y privacidad

- `validation/`: instalaciones limpias, entornos de prueba, copias de recursos locales, resultados físicos, capturas y logs crudos que pueden contener rutas privadas.
- `.cache/`: bloqueos, registro local de importación y avisos de la carpeta privada de origen.
- `.venv/`, `__pycache__/`, `tests/.tmp/`, `*.pyc`, `*.pyo`, `*.tmp` y `*.part`: material regenerable.
- `app/RoboPenalty/phase9a/results/`: salidas nuevas de la partida.
- `app/RoboNaldo_Deploy/**`: exclusión por defecto, con excepciones exactas para los 35 STL BSD, su licencia, README y cinco `__init__.py` vacíos. Los 26 destinos pendientes siguen ignorados.
- `*.onnx`, `*.npz`, audio, video y ZIP: no se versionan pesos, movimientos, grabaciones ni paquetes históricos.
- `.env` y variantes, claves/certificados privados, logs y configuración local de IDE: protección adicional para una publicación pública.

No se borraron archivos. Las copias locales necesarias para la prueba permanecen en disco. No se encontraron repositorios Git anidados, `.gitmodules`, enlaces/reparse points ni rutas personales en el conjunto público. El escaneo buscó rutas privadas, claves, tokens, credenciales y nombres de dispositivos; no demuestra ausencia absoluta de cualquier secreto imaginable.

Las frases de `phase9a/fixtures/directed.json` son órdenes de prueba programadas, no transcripciones personales capturadas. Los WAV, logs de micrófono y transcripciones de pruebas reales están excluidos.

`.gitattributes` conserva bytes (`* -text`), incluidas calibraciones y modelos BSD; no normaliza LF/CRLF. Ningún archivo público supera 50 MiB ni el límite de bloqueo de 100 MiB de GitHub. No hace falta Git LFS para esta selección. [Límites oficiales](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

## Licencias y límites de distribución

Se conservaron completos los avisos y las condiciones BSD-3-Clause de [Unitree MuJoCo](https://github.com/unitreerobotics/unitree_mujoco/blob/1eb6642e3f3fdfb7fb13a9794fd6a2dd93ea0e7d/LICENSE) y [Unitree ROS](https://github.com/unitreerobotics/unitree_ros/blob/38a9b00ecbff0b70e85a7627eb9c65db9a2341f7/LICENSE), con sus revisiones congeladas y hashes. Los archivos de licencia y los recursos incluidos coinciden con los manifiestos; no se presenta a Unitree como patrocinador.

Los 26 recursos Deploy permanecen fuera de la publicación. Sus nombres, fuentes y hashes son metadatos; no se incluyen contenidos, parches derivados ni las políticas. El motor genérico de reconstrucción utiliza fixtures propios en los tests. Una copia oficial sola necesita ocho modificaciones y tres adiciones TP07; no se redistribuyen esas adaptaciones automáticamente.

La importación local valida bytes y conserva avisos, pero no concede permisos. Cada integrante debe disponer legítimamente de una copia adaptada compatible. La descarga automática de esos recursos sigue bloqueada. El equipo todavía debe acordar la licencia de su código propio: hacer público el repositorio no equivale a otorgar una licencia de software abierto. No se eligió una licencia en nombre del equipo. Detalle: `../THIRD_PARTY.md`.

## Validaciones y alcance de las afirmaciones

- Batería de paquete y componentes: 134 tests; los resultados del cierre se conservan en el directorio local de auditoría.
- Inventario SHA-256 público y perfiles históricos sin alterar; verificación exacta del catálogo y las 37 calibraciones.
- Diagnóstico esperado sin importación: 78/104, exactamente 26 faltantes y lanzadores bloqueados.
- Diagnóstico de la copia aislada importada: 104/104 correctos y ejecución local habilitada; permisos de redistribución reportados por separado.
- Sintaxis de los siete scripts PowerShell y revisión estática de los comandos del README.
- Auditoría del conjunto real admitido por Git, no solo de la lista anterior del inventario.

La validación física previa de la importación local completó tandas automática, dirigida y dirigida con visor, 35.000 pasos cada una, con igualdad exacta de los estados y trazas comparados frente a 8C. No se repitieron esas tandas durante una auditoría que solo modifica documentación y exclusiones; no se atribuyen nuevas pruebas físicas a este cierre. Ver `LOCAL_IMPORT_RESULTS.md` para métricas, campos comparados y exclusiones.

## Correcciones de este cierre

README ampliado con arquitectura, autoría, política preentrenada, requisitos, instalación, importación, comandos, pruebas, limitaciones y créditos. `.gitignore` reforzado frente a pesos y archivos privados fuera de las carpetas habituales, sin ocultar calibraciones. Documentación de pendientes actualizada para distinguir la importación local ya validada de la descarga/redistribución no habilitada. Encabezado de importación en THIRD_PARTY corregido. Inventario SHA-256 renovado únicamente por estos cambios propios.

Los informes antiguos `script_checks.json`, `INSTALLER_RESULTS.json`, `privacy_review.json` y `source_preservation.json` documentan pasos anteriores y se conservan como tales; no reemplazan este cierre ni deben interpretarse como diagnóstico actual.

## Publicación manual desde VS Code

Crear manualmente un repositorio público vacío en GitHub, sin README, licencia ni `.gitignore` automáticos. Desde la raíz de esta distribución, después de revisar este informe:

```powershell
git init -b main
git config core.autocrlf false
git add --dry-run .
# Revisar que no aparezcan validation, .venv, .cache, ONNX, NPZ ni recursos Deploy pendientes.
git add .
git diff --cached --stat
git diff --cached --name-only
# Detenerse si la selección difiere del inventario público revisado.
git commit -m "chore: prepare RoboPenalty AI handoff through phase9a"
$repo = Read-Host "URL HTTPS del NUEVO repositorio público vacío"
git remote add origin $repo
git push -u origin main
```

Estos comandos son instrucciones para el usuario; **no se ejecutaron**. No usar `git add -f` ni force push. Si el remoto contiene historia o el push se rechaza, detenerse y revisar el destino; no sobrescribirlo. Revisar también nombre/correo configurados en Git antes del commit y usar el correo noreply de GitHub si se desea evitar publicar un correo personal.

## Limitaciones que permanecen

La simulación requiere los 26 archivos locales compatibles; no hay un canal de redistribución automático habilitado para ellos. La voz no está validada como funcional. La instalación limpia fue probada en esta computadora, no en otra máquina física. Las pruebas nominales no prueban robustez global de todos los tiros. El repositorio aún no fue creado ni publicado, por lo que no existe URL ni SHA nuevos que informar.
