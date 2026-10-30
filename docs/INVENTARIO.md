# Inventario y separacion de distribucion/instalacion

El codigo fisico, agentes, catalogo 8C y 37 calibraciones mantienen sus bytes. Se conservan los helpers transitivos de las fases anteriores. La implementacion nueva pertenece solo a portability, scripts, tests y documentacion; no se modifica ningun proyecto de referencia.

copied_files.json conserva los hashes de origen de las copias iniciales y documenta las adaptaciones de portabilidad/preflight. authorized_resources.json documenta los 35 meshes adicionales descargados desde Unitree ROS y los cinco vacios generados; sus hashes coinciden con los registros congelados. La licencia exacta Unitree ROS esta en app/RoboNaldo_Deploy/LICENSE-Unitree-ROS.txt; la anterior de MuJoCo se conserva tambien.

external_sources.json registra las 66 entradas y su aviso adicional: fuentes fijadas, categoria, permisos, hashes y tamanos. Se incluyen metadatos de los 26 pendientes, NO sus archivos o parches. Los originales runtime_profile.json y external_manifest.json no se editan. distribution_profile.json ancla ambos perfiles aplicables y la politica por recurso, sin exigir .git externo.

distribution_inventory.json enumera el conjunto publicable por SHA-256; se excluye a si mismo para evitar circularidad. No es una firma autenticada. La carpeta validation contiene copias limpias/entornos/logs de prueba LOCALES y queda excluida. Tambien se excluyen .cache, .venv, *.part, audio, ZIP, caches y resultados nuevos. Los 37 JSON de phase8c/results no estan ignorados.

.gitignore utiliza una lista de inclusion exacta para los 35 STL BSD y cinco vacios dentro de RoboNaldo_Deploy; el resto permanece ignorado, incluso si en el futuro se instala localmente. No usar git add -f para eludirla. El contenido publicable no contiene ONNX, NPZ ni codigo sustantivo de Deploy; las copias de validacion local estan excluidas.

Los registros anteriores de source_preservation y escaneo se conservan como evidencia de preparacion; la comprobacion nueva se documenta en VALIDACION.md. No se ejecuto Git init, commit o push.
