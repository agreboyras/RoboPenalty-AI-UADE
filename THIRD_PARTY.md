# Procedencia, permisos y avisos

## Recursos incluidos con licencia comprobada

1. Unitree MuJoCo: LICENSE, unitree_robots/g1/g1_29dof.xml y 36 meshes del perfil. Repositorio unitreerobotics/unitree_mujoco; revision 1eb6642e3f3fdfb7fb13a9794fd6a2dd93ea0e7d. BSD-3-Clause, Copyright (c) 2016-2024 HangZhou YuShu TECHNOLOGY CO.,LTD. Aviso completo sin cambiar: app/unitree_mujoco/LICENSE.
2. Unitree ROS: 35 meshes identicos a los requeridos en g1_description/meshes. Fuente oficial unitreerobotics/unitree_ros, revision 38a9b00ecbff0b70e85a7627eb9c65db9a2341f7, robots/g1_description/meshes/. Coinciden los blobs Git y los SHA-256 congelados. BSD-3-Clause, Copyright (c) 2016-2022 HangZhou YuShu TECHNOLOGY CO.,LTD. Licencia exacta adicional: app/RoboNaldo_Deploy/LICENSE-Unitree-ROS.txt. Se conservan ambas licencias, sin sustituir una por otra. No se usa Unitree como respaldo del producto.
3. Cinco __init__.py vacios se generan como estructura propia (cero bytes); no atribuyen licencia al resto del directorio.

Fuentes/licencias: https://github.com/unitreerobotics/unitree_ros/blob/38a9b00ecbff0b70e85a7627eb9c65db9a2341f7/LICENSE ; https://github.com/unitreerobotics/unitree_mujoco/blob/1eb6642e3f3fdfb7fb13a9794fd6a2dd93ea0e7d/LICENSE . El manifiesto external_sources.json registra rutas, commits, hashes y estados por archivo.

## Recursos no incluidos y NO habilitados automaticamente

OpenDriveLab/RoboNaldo_Deploy, revision f60f24459aaabc3aea9187a2b13f8923049b629c: codigo base, configuraciones, XML, politica policy-obs-aic.onnx y movimiento freekick_motion.npz que siguen pendientes. TP07 adaptado: agreboyras/TP07-IA-G1-Futbol, revision ce4b34d1bccfd0420a81bf1688271d86feb8a117; ocho modificados y tres anadidos estan identificados, sin dar por propia toda su implementacion.

El repositorio RoboNaldo tiene LICENCE MIT. No se encontro una extension expresa al conjunto Deploy y sus pesos; el submodulo mantiene procedencia independiente. El movimiento fuente tiene los mismos valores numericos, pero otro hash/serializacion. No se sustituye el NPZ congelado por otro. Tampoco se aplica la licencia BSD de los meshes a los XML o controladores de Deploy.

Hay 26 pasos pendientes. Sus URL HTTPS exactas y hashes se describen, pero no se descargan ni se ejecutan por una bandera de aceptacion. No se incluye codigo, contenido de diferencias, parches derivados, ONNX ni NPZ de ese conjunto en el paquete publicable. El mecanismo generico de reconstruccion es propio; en el futuro requeriria dos fuentes verificadas y permisos revisados, no una supuesta autorizacion creada por el instalador.

Atribuciones: Deploy reconoce como base ccrpRepo/RoboMimic_Deploy; su alcance debe aclararse con los titulares. TP07 debe revisar la autoria de sus contribuciones. Un repositorio publico o privado no reemplaza esa revision. Para habilitar los pasos pendientes se necesita revisar evidencia y actualizar de forma expresa la politica y su inventario; no basta cambiar una opcion de linea de comandos.

## Paquetes, voz y codigo propio

Los paquetes Python se obtienen desde PyPI y no se incluyen en Git; conservar los avisos de sus distribuciones. No se descargan pesos Whisper, audio ni SDK de robot real. Voz opcional no validada. El equipo aun debe acordar la licencia de su codigo; no se crea una LICENSE global que cubra a terceros.
## Importacion local

El usuario puede seleccionar una copia Deploy adaptada que ya posea legitimamente. El importador valida los 26 recursos pendientes contra el perfil congelado, conserva avisos y los coloca en rutas locales excluidas de Git. Esto habilita solo una ejecucion local con integridad comprobada; no concede ni afirma permisos de uso o redistribucion. La descarga de los recursos pendientes sigue desactivada. No se incluyen parches derivados del Deploy. Procedimiento: docs/IMPORTACION_LOCAL.md.

La opcion tecnica CRLF->LF del manifiesto se limita a la importacion de 24 textos y exige el SHA-256 canonico existente. No cambia el estado `authorization: pending`, no concede derechos y no se aplica a ONNX, NPZ ni avisos de licencia. Los avisos conservan sus bytes originales.

