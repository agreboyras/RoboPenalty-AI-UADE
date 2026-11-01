# Hito 1: G1 libre dentro del estadio

Experimento independiente. **Solo equilibrio y un penal: no implementa una atajada,
no usa goalkeeper.pt y no reemplaza los modos públicos de 8C/9A.**

## Ejecutar en esta computadora

Desde la raíz de RoboPenalty-AI-Complete:

```powershell
# Arquero de pie en el centro; tiro físico lateral existente; visor 7D.
.\scripts\probar_estadio_libre_h1.ps1 -Ubicacion centro -Viewer -Camara behind

# Verificar el tiro con el arquero físicamente apartado (Y=4 m).
.\scripts\probar_estadio_libre_h1.ps1 -Ubicacion apartado -Viewer -Camara overview

# Opcional: guardar capturas reales iniciales y finales en las cuatro cámaras.
.\scripts\probar_estadio_libre_h1.ps1 -Ubicacion centro -Viewer -Camara behind -Capturas

# Referencia del mismo tiro sin arquero; no abre ventana.
.\scripts\probar_estadio_libre_h1.ps1 -Ubicacion sin-arquero
```

Todos ejecutan 14 segundos simulados / 7000 pasos a 500 Hz. El tiro predeterminado
es right_inter_m080, sin cambios de bias o condiciones iniciales respecto de 8C.
El arquero permanece con comando de locomoción físicamente cero; no recibe la
etiqueta del tiro ni observa la pelota. No se selecciona todavía una maniobra.
El visor puede ir más lento que tiempo real; nunca saltea pasos para compensarlo.
Se cierra al terminar, con la X o Ctrl+C. Cierre anticipado significa ensayo
incompleto, no una atajada ni un penal completo.

## Dependencias existentes y rutas

No se instala ni descarga nada. El lanzador usa:

- Python del juego: .venv si existe; en esta máquina, como alternativa explícita,
  validation/etapa2_final_20261030/RoboPenalty AI UADE/.venv.
- Python de inferencia: validation/keeper_balance4b/.venv.
- FreeKick: app/RoboNaldo_Deploy si está importado; de lo contrario la copia local
  validada validation/keeper_live_20261030/package/app/RoboNaldo_Deploy.
- G1 original: app/unitree_mujoco/unitree_robots/g1/g1_29dof.xml.
- Locomoción externa: ../RoboNaldo_Deploy/policy/loco_mode/model/policy_29dof.pt,
  más las dos configuraciones verificadas por el adaptador de 4B.1.

Se pueden indicar -Python, -PolicyPython, -DeployPath y -LocoDeployPath. No se
buscan recursos en carpetas desconocidas ni se omiten los SHA-256 para ejecutar.
Un clon público sin recursos externos y sin estos entornos privados no es suficiente.
Los permisos de redistribución de pesos siguen pendientes; no se incluyen aquí.

## Arquitectura

- scene.py compone el MJCF existente de FreeKick con el G1 original mediante
  MjSpec.attach. Conserva la raíz libre y no crea slider, carro, anclaje ni fuerzas
  de equilibrio. Quita solo keyframes de la instancia adjunta, antes de compilar.
- La pose y altura iniciales del arquero se establecen antes del primer paso,
  usando la home de 4B.1 y 1 mm de separación de las suelas físicas. No se escribe
  su qpos/qvel para moverlo durante el ensayo.
- Se verifican masas, inercias, geometrías, fricciones, parámetros articulares,
  actuadores, orden y ausencia de solapamiento de índices. Los arrays físicos
  originales del delantero/escena deben conservar su prefijo exactamente.
- policy_worker.py reutiliza Locomotion de 4B.1 en un proceso CPU separado. Solo
  transforma observaciones del arquero en referencias articulares a 50 Hz. No
  importa ni crea MuJoCo. Reinicia LSTM, verifica checkpoint/configuraciones y
  normalizador. La observación y el checkpoint permanecen intactos.
- run.py es el único propietario del mundo físico. Aplica una única asignación
  de torques del arquero por paso: referencia → PD de 4B.1 → límites efectivos.
  No se superponen PosturePD, control de slider, residuales ni política 4C.
- FreeKickAdapter y scenarios.initialize se importan sin modificar. Se conserva
  el orden temporal del runner histórico: torque/step y actualización FreeKick
  después del paso cada diez iteraciones.
- presentation.py solo sustituye el overlay que dependía del slider. Reutiliza
  íntegramente MonumentalPresenter/estadio/publicidad 7D y sus guardas de física.

La separación en dos procesos evita mezclar entornos científicos incompatibles.
El proceso auxiliar nunca escribe motores: sus respuestas secuenciadas llegan
sin avanzar tiempo físico mientras se espera. Hay timeout y cierre del proceso.
La latencia RPC se mide y no se interpreta como una frecuencia garantizada.

## Criterios declarados antes de las pruebas

14 s, 7000 pasos, finitud, fuerzas externas nulas; raíz libre; torque único;
contacto físico pie-pelota; sin avisos de motor; arquero con inclinación <15°,
deriva horizontal <0.10 m y pelvis >=0.50 m. Sin contactos indebidos en estos
ensayos de espera, sin violaciones articulares, sin saturación continua >=0.10 s
y penetración del arquero <=0.01 m. Las referencias se recortan a rangos como en
4B.1: se registran los seis recortes iniciales, no se ocultan ni se amplían límites.

La penetración global se informa separadamente: el contacto pie-pelota original
ya puede superar 1 cm. El umbral de 1 cm pertenece al arquero, no se usa para
cambiar o recalibrar el contacto de FreeKick.

## Resultados y pruebas

Ver RESULTADOS.md. Salidas nuevas bajo validation/free_keeper_stadium_h1,
excluidas de Git. report.json registra criterios y resultado; contacts.json
incluye contactos físicos; composition.json mapea índices y compatibilidad;
trace.npz contiene ball (tiempo, posición, velocidad), shooter (q29,dq29,ctrl29,
raíz q7,v6), keeper (tiempo, raíz q7,v6,q29,dq29,ref29,ctrl29,torque real29),
decisions (tiempo, obs96, objetivo original29 y recortado29), stability.

Las fuerzas/contactos son del solver previo a integrar; se conservan tanto
solver_time_s como sampled_time_s. No se llama mj_forward durante el bucle para
recalcular contactos a posteriori.

```powershell
$pythonH1 = (Resolve-Path "validation/etapa2_final_20261030/RoboPenalty AI UADE/.venv/Scripts/python.exe").Path
Push-Location app/RoboPenalty
try {
  & $pythonH1 -X utf8 -B -m unittest experiments.free_keeper_stadium_h1.test_hito1 -v
} finally { Pop-Location }
```

Los tests de composición necesitan la importación local indicada; se omiten
explícitamente si no existe, sin descargarla. Las pruebas no sustituyen un ensayo
físico. No se actualizó el inventario público de las fases estables: una futura
publicación de este nuevo módulo requiere su revisión e incorporación al inventario.
