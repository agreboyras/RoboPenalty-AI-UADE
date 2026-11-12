# Hito 2: maniobra lateral física, manual y aislada

## Estirada centrada

`-Ensayo maniobra` abre la prueba manual nueva con el G1 frente al arco, en
`(X=4.38, Y=0)`. El G1 arranca en guardia semiflexionada, empuja con la pierna
contraria al lado elegido y recoge el codo al aterrizar. El visor encuadra los
dos postes desde la cancha y prescinde de las tribunas. Cada ensayo integra
2,4 s de física a 500 Hz, con 0,39 s de guardia. La pelota queda en reposo y el
ensayo muestra el movimiento del arquero en aislamiento.

Desde la raíz de `RoboPenalty-AI-UADE`:

```powershell
.\scripts\probar_maniobra_h2.ps1 -Ensayo maniobra -Lado LEFT -Viewer
.\scripts\probar_maniobra_h2.ps1 -Ensayo maniobra -Lado RIGHT -Viewer
```

Sin `-Viewer` se ejecuta headless. `-Capturas` guarda las fases y la pose final.
Esta variante usa el Python del juego y los MJCF y mallas del campo y del G1.
Cada corrida guarda `report.json` con tiempos, posición inicial/final y alcance
entre postes, más las posiciones de pelvis y muñeca a 500 Hz.

## H2 histórico

Estado técnico: APROBADO para este laboratorio nominal. No demuestra una atajada,
una reacción autónoma ni una zambullida humana afinada. Reutiliza sin modificar el
mundo del Hito 1 y la presentación 7D; el arquero empieza en X=4.2, Y=4 m para
separar la maniobra del tiro. FreeKick y la pelota siguen funcionando con el
preset histórico right_inter_m080, pero no se evalúa un resultado de atajada.

## Ver en esta computadora

Abrir PowerShell en la raíz de RoboPenalty-AI-UADE, ejecutar una orden por vez:

```powershell
# Referencia: equilibrio sin maniobra, 6 segundos simulados.
.\scripts\probar_maniobra_h2.ps1 -Ensayo equilibrio -Viewer

# Transferencia sin movimiento nuevo: política hasta 2 s, referencia propia fija
# hasta 3 s; no salta la referencia ni se modifica la raíz.
.\scripts\probar_maniobra_h2.ps1 -Ensayo transicion -Viewer

# Izquierda y derecha, desde la perspectiva del delantero mirando el arco.
.\scripts\probar_maniobra_h2.ps1 -Ensayo maniobra_historica -Lado LEFT -Viewer
.\scripts\probar_maniobra_h2.ps1 -Ensayo maniobra_historica -Lado RIGHT -Viewer

# Opcional: cinco capturas físicas (equilibrio, preparación, impulso, extensión y final).
.\scripts\probar_maniobra_h2.ps1 -Ensayo maniobra_historica -Lado LEFT -Viewer -Capturas
```

LEFT es +Y mundial y usa principalmente el brazo anatómico derecho del arquero;
RIGHT es -Y y usa el izquierdo. La cámara de laboratorio muestra al arquero
apartado dentro del estadio, con delantero y pelota en la misma simulación.
Cerrar con X o Ctrl+C. Un cierre temprano registra un ensayo incompleto.
No hay reinicio mientras cae ni recuperación autónoma; se crea un mundo nuevo
al ejecutar nuevamente el comando.

El visor intenta ritmo 1x y puede ir más lento. La carga inicial usa varios
segundos y las capturas agregan pausas reales sin avanzar tiempo físico.
No interpretar tiempos de sync/captura como FPS.

## Secuencia y propiedad del control

| Tiempo simulado | Estado | Referencias |
|---|---|---|
| 0–2 s | BALANCE | Política externa 4B.1, velocidad deseada cero |
| 2–2.2 s | TAKEOVER | Última referencia de la política, sin salto |
| 2.2–3 s | PREPARING | Flexión bilateral, apertura moderada de brazos |
| 3–3.55 s | LATERAL_PUSH | Extensión de rodillas y referencias laterales de cadera/tobillos |
| 3.55–4.2 s | EXTENDING | Brazo del lado elegido y cintura; caída permitida |
| 4.2–4.8 s | FINALIZING | Transición suave hacia una instantánea articular real acotada |
| 4.8–6 s | FINISHED_HOLD | Mantener esa referencia; no levantarse |

La última inferencia de política ocurre a 1.98 s; son 100 decisiones a 50 Hz.
Después el proceso auxiliar permanece sin solicitudes hasta cerrarse. Un único
PD a 500 Hz, en el proceso de MuJoCo, escribe los 29 motores. Las ganancias y
límites efectivos son los de H1. No se superponen residuales ni otro PD.
La primera referencia propia coincide exactamente con la última referencia
recortada de la política. Los segmentos propios son quinticos de extremos con
velocidad/aceleración cero. No hay asignaciones a qpos/qvel de pelvis durante
el episodio, fuerzas externas, anclajes, cambios de contactos ni políticas 4C.

La preparación agrega a la referencia capturada rodillas +0.18 rad, caderas
pitch -0.09 y tobillos pitch -0.09. Participan también caderas roll, tobillos roll,
cintura roll/pitch, hombros pitch/roll y codos. Las demás articulaciones conservan
su referencia capturada. Las metas completas por articulación se registran en
trajectory_targets.json; la trayectoria efectiva y el movimiento real están en
trace.npz. No todos los objetivos se alcanzan exactamente.

## Límites declarados antes de los ensayos laterales

Aceptación: movimiento de pelvis >=0.20 m, muñeca seleccionada >=0.30 m y extensión
lateral relativa muñeca–hombro >=0.10 m, todos hacia el lado elegido desde la
transferencia. Referencia <=3 rad/s y <=20 rad/s²; velocidad articular real <=20 rad/s;
penetración del arquero <=2 cm; exceso de límite articular blando <=0.03 rad.
Parada inmediata: penetración >3 cm, exceso articular >0.10 rad, velocidad >40 rad/s,
NaN o fuerza externa. Se registra toda caída y saturación sin reiniciar el episodio.
Estos son criterios del laboratorio, no una declaración de seguridad de un robot
real. No se ampliaron límites del modelo ni torques. Caer intencionalmente no es
un fallo por sí solo. Los umbrales no se relajaron después de medir.

## Dependencias y salidas

El lanzador reutiliza las mismas rutas privadas ya existentes del Hito 1: Python
estable de validation/etapa2_final_20261030/RoboPenalty AI UADE/.venv, Python CPU
validation/keeper_balance4b/.venv, FreeKick importado en
validation/keeper_live_20261030/package/app/RoboNaldo_Deploy, y la política externa
../RoboNaldo_Deploy/policy/loco_mode/model/policy_29dof.pt. No instala ni descarga
nada. Este lanzador es para la instalación local auditada; un clon público solo
no contiene esos recursos/entornos. No se copian ni autorizan pesos externos.

Salidas nuevas en validation/lateral_keeper_h2 (excluido de Git): configuración,
metas articulares, reporte, contactos, capturas y trazas. Columnas de frames:
tiempo, posiciones de pelvis/muñeca izquierda/derecha/hombro izquierdo/derecho
(5×3), inclinación, q29, dq29, referencia29, torque solicitado29, torque enviado29,
torque real29. world conserva tiempo/qpos/qvel/ctrl del mundo completo.
policy conserva tiempo/obs96/salida29/referencia recortada29. Las posiciones y
fuerzas corresponden al estado nativo previo a integrar en el tiempo registrado.
Las muñecas son la referencia de mano usada; no se afirma una palma física nueva.

## Tests

```powershell
$pythonH2 = (Resolve-Path "validation/etapa2_final_20261030/RoboPenalty AI UADE/.venv/Scripts/python.exe").Path
Push-Location app/RoboPenalty
try {
  & $pythonH2 -X utf8 -B -m unittest experiments.lateral_keeper_h2.test_maneuver experiments.free_keeper_stadium_h1.test_hito1 -v
} finally { Pop-Location }
```

Los tests sintéticos no demuestran movimiento: ver RESULTADOS.md para ensayos
físicos, trazas exactas y capturas reales. El inventario de distribución estable
no se modifica; antes de publicar estos archivos nuevos será necesaria su auditoría.
Hito 3 no implementado.
