# Pasos pendientes, sin bloquear el desarrollo autorizado

El perfil runtime original de 104 recursos y el historico de 209 mantienen sus hashes. Ya estan preparados 78 recursos: los 38 Unitree anteriores, 35 meshes BSD adicionales y cinco __init__.py vacios. La licencia Unitree ROS se conserva como aviso adicional fuera del conteo runtime.

Permanecen 26 pasos, todos enumerados en pending_resources.json y external_sources.json: 15 originales no vacios (incluidos ONNX, NPZ y g1_liao.xml), ocho modificados y tres anadidos TP07. No se obtienen automaticamente, ni por una opcion --acepto, ni porque exista un repositorio publico. Los permisos pendientes se muestran por recurso y en el estado final.

Los ocho modificados son common/logger.py, common/utils.py, deploy_mujoco/config/mujoco_freekick.yaml, deploy_mujoco/deploy_mujoco.py, g1_description/scene_with_ball.xml, policy/fixedpose/FixedPose.py, policy/robonaldo/FreeKick.py y policy/robonaldo/config/freekick.yaml. Cada paso tiene hash base oficial y hash final exacto. Las tres adiciones son celebration_coordinator.py, policy/celebration/Celebration.py y policy/celebration/__init__.py.

La base es OpenDriveLab/RoboNaldo_Deploy f60f24459aaabc3aea9187a2b13f8923049b629c. La version TP07 es agreboyras/TP07-IA-G1-Futbol ce4b34d1bccfd0420a81bf1688271d86feb8a117. El motor generico de recetas efimeras esta implementado, sin distribuir parches derivados ni fuentes pendientes. Hoy su entrada de red esta deshabilitada para esos pasos. Ver INSTALADOR.md para la dependencia explicita de ambos archivos verificados.

La importacion local ya permite completar esos 26 recursos desde una copia adaptada obtenida legitimamente, sin cambiar la politica de descarga ni los hashes. Fue validada en una carpeta y entorno nuevos con tandas automatica, dirigida y con visor, con equivalencia fisica exacta en los estados y trazas comparados. Ver IMPORTACION_LOCAL.md y LOCAL_IMPORT_RESULTS.md.

Pendiente: que cada integrante disponga de esa copia compatible bajo condiciones aplicables; validar el procedimiento en otra computadora fisica; y aclarar permisos/autoria antes de habilitar una descarga o redistribucion de Deploy. La prueba local no convierte esos recursos en contenido publicable. No es necesario cambiar la politica para ejecutar una importacion local ya verificada.
