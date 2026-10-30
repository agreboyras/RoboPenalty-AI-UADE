# Importación local LF/CRLF — Etapa 2

Esta revisión acepta copias legítimas compatibles de Deploy con LF o CRLF en sus textos, sin convertir el origen ni aceptar contenido diferente. No habilita descargas o redistribución de los 26 recursos pendientes.

## Política explícita

`portability/external_sources.json` enumera 24 entradas con:

```json
"local_import_text": {
  "encoding": "utf-8",
  "newline_transform": "crlf-to-lf"
}
```

Son exactamente los 24 recursos de texto pendientes del perfil: Python, XML y YAML. La extensión sola no autoriza la transformación; la entrada debe incluir esta política y pertenecer a una categoría permitida. ONNX, NPZ y los demás recursos no tienen esta opción. Una opción de texto aplicada a un binario se rechaza como política inválida.

1. Se calcula el SHA de los bytes recibidos. Si coincide con el SHA canónico, se conserva exactamente la entrada.
2. Solo si la política lo permite, se valida UTF-8 estricto y se sustituyen exclusivamente los pares de bytes CRLF por LF, sin decodificar/regrabar el contenido.
3. Se rechazan CR aislados, NUL y cualquier resultado cuyo SHA no sea exactamente el existente en el perfil. No se eliminan BOM, espacios, tabulaciones ni saltos finales, ni se convierten codificaciones. Mezclas LF/CRLF solo pasan si esta misma operación produce el SHA canónico.
4. Antes de escribir se validan todos los recursos y se comprueban destinos existentes. Un destino diferente no se repara ni se sobrescribe silenciosamente.
5. Se escribe una copia local atómica y se vuelve a comprobar el SHA exacto instalado. El verificador de los 104 recursos sigue siendo estricto; no normaliza archivos instalados.

Los avisos LICENSE/NOTICE/README de procedencia se preservan byte a byte en la caché local, incluso si contienen CRLF. La fuente se abre únicamente para lectura.

## Integridad y compatibilidad

Los hashes de cada recurso, el perfil runtime 104 y el manifiesto histórico 209 se mantienen. Cambia el hash del archivo `external_sources.json` porque contiene metadatos nuevos; su ancla en `distribution_profile.json` y el inventario propio se actualizan expresamente. No se sustituyen hashes de recursos para aceptar variantes.

Las licencias/acciones de descarga del manifiesto no cambian: los 26 siguen `pending`. La política de texto no es un permiso de uso o redistribución.

El registro de importación conserva formato versión 1 y añade SHA de origen y transformaciones por recurso. Los registros anteriores siguen siendo válidos cuando los destinos conservan sus hashes canónicos. Las rutas personales de origen no se guardan. Los nuevos campos son trazabilidad técnica, no una firma ni prueba de licencia.

## Uso desde esta distribución actualizada

```powershell
.\scripts\importar_deploy.ps1 -DeployPath '..\Deploy Compatible' -Inspeccionar
.\scripts\instalar.ps1 -NoInteractivo -DeployPath '..\Deploy Compatible'
.\scripts\verificar.ps1
```

La inspección informa `adapted` para bytes ya exactos y `crlf_to_lf` para textos aceptables mediante la operación. Ambos son compatibles; `official_base`, `different` o `missing` no habilitan una importación completa. Un Deploy oficial sigue necesitando las modificaciones TP07: la normalización no las crea.

Esta corrección está preparada en RoboPenalty-AI-Complete. No se modifica el clon de prueba ni se publica el cambio automáticamente: un clon con el importador anterior seguirá rechazando CRLF hasta que se actualice mediante un paso posterior autorizado.

## Resultados comprobados el 30/10/2026

- **170 tests aprobados:** 144 de regresión y 26 nuevos de bytes/política/importación. Se conserva el rechazo de CRLF para textos sin opción explícita. El verificador de destinos sigue rechazando CRLF instalado, aun cuando la importación de esa fuente esté permitida.
- Dos copias nuevas del contenido público bajo validation, sin repositorios Git ni modelos pendientes incluidos en el paquete inicial. Se ejecutó el instalador real con `-SoloRecursos -NoInteractivo` y después un diagnóstico completo con el intérprete 3.12 y paquetes ya disponibles dentro de la distribución; no se instalaron dependencias nuevas.
- Fuente original: 5 recursos ya exactos y 21 textos CRLF. Se importaron 26 y se transformaron 21 únicamente en el destino. Instalador código 0; diagnóstico completo 104/104, inventario correcto y ejecución local apta.
- Fuente compatible LF: 26 ya exactos, cero transformaciones. Código 0 y diagnóstico completo 104/104 apto.
- Los 104 hashes de ambos destinos son idénticos, incluidos ONNX y NPZ. No se cambiaron los SHA de ningún recurso ni los archivos de manifiesto histórico 209/perfil runtime 104.
- SHA de los 26 archivos de cada fuente comprobados antes/después, sin cambios. Los 232 archivos publicables del clon de prueba también conservaron sus hashes. No se escribió en los proyectos originales ni en ese clon.
- Un registro real de instalación LF anterior sigue siendo aceptado por el importador nuevo. También se prueba el formato anterior de registro sin campos opcionales nuevos.
- Los avisos se conservaron byte a byte; siguen pendientes los permisos de los 26 recursos y la descarga automática continúa deshabilitada.

Los tests nuevos cubren LF, CRLF, mezcla de ambos, espacios/tabulaciones, BOM, UTF-16/Latin-1, CR aislado, saltos finales alterados, binarios exactos y modificados, política inválida sobre binarios, archivos no enumerados, copia canónica, origen intacto, cambio de fuente entre inspección y lectura y destino previamente alterado.

Las evidencias completas están bajo `validation/line_endings_20261030/`, excluidas de Git. No se repitieron tandas físicas: esta etapa valida la importación y la identidad exacta de sus salidas; no modifica controladores, políticas ni parámetros físicos y no atribuye nuevas mediciones de juego.

Los 26 recursos no se incorporan al contenido publicable. Los cambios siguen locales, sin add, commit ni push. El clon de prueba mantiene su versión anterior hasta una actualización posterior autorizada.
