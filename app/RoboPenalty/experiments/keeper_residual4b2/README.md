# 4B.2: referencia residual acotada

Protocolo fijado antes de ejecutar la primera simulación. Variante privada,
independiente de 4B.1 y de los modos públicos. No incluye políticas externas.

La política de locomoción sigue siendo el controlador principal. Se reutilizan
sin cambios su adaptador, observaciones, normalizador, memoria recurrente,
escalas, ganancias, postura inicial y composición de base libre de 4B.1.
Solo se reinicia h/c al inicio de cada ensayo, como en 4B.1; durante el ensayo
evoluciona normalmente. La última acción observada sigue siendo la salida cruda
de la política: no se reemplaza por el residual ni por una acción inventada.

Un único cálculo produce la referencia final:
`clip(referencia_politica + residual, limites_articulares)` y un único PD produce
torques, sujetos a los mismos límites efectivos. No hay otro escritor de motores,
cambios de ganancias, fuerzas sobre la base ni escrituras de qpos/qvel al simular.

## Maniobra autorizada

Solo bilateral hip_pitch -0.01 rad, knee +0.02 rad y ankle_pitch -0.01 rad.
Las otras 23 articulaciones reciben residual cero. Amplitudes no configurables.

| Tiempo | Residual |
|---|---|
| 0–3 s | Cero, asentamiento idéntico a 4B.1 |
| 3–5 s | Rampa quíntica 0→1, velocidad y aceleración nulas en extremos |
| 5–6 s | Mantener amplitud |
| 6–8 s | Rampa quíntica 1→0 |
| 8–10 s | Cero, recuperación libre del controlador |

Política y residual a 50 Hz, PD y física a 500 Hz, 500 decisiones y 5000 pasos.
La interpolación de la envolvente es suave; las referencias se mantienen entre
decisiones, igual que el contrato de control original.

## Interrupción inmediata y criterios de seguridad

- Roll o pitch absoluto >=15°, deriva horizontal >=0.10 m, pelvis <0.50 m.
- Cualquier contacto no pies-suelo, autocolisión incluida.
- Penetración de contacto >5 mm (baseline registrado: 4.33 mm).
- Velocidad articular absoluta >8 rad/s (baseline: 5.38 rad/s).
- Posición articular fuera del rango efectivo, tolerancia numérica 1e-6 rad.
- Torque aplicado fuera del límite efectivo, tolerancia 1e-9 Nm.
- Saturación solicitada continua >=0.10 s en cualquier motor.
- Fuerza externa, estado no finito o advertencia de MuJoCo.

No se reinicia ni recupera artificialmente una simulación interrumpida. El visor
también puede cerrarse, registrando el ensayo como incompleto. El mínimo de
límites de modelo y Deploy se conserva; no se aumenta fuerza ni recorrido.

## Criterios de movimiento y recuperación

Se compara SOLO DESPUÉS de terminar con las posiciones reales de 4B.1 en los
mismos tiempos. El baseline no es una observación del agente ni guía el control.

- Ventana de flexión 5.5–6 s: incremento medio real de cada rodilla >=0.005 rad
  (25% del residual solicitado), y descenso medio de pelvis >=0.5 mm.
- Ventana de recuperación 9–10 s: error absoluto medio de cada una de las seis
  articulaciones intervenidas <=0.005 rad y de altura de pelvis <=2 mm.
- Estado físico idéntico al baseline hasta 3 s; tres repeticiones exactamente
  reproducibles; sin criterios de seguridad incumplidos.

Mantenerse de pie no basta. Si falla flexión o recuperación no se aumenta la
amplitud ni se modifican ganancias; se documenta el resultado y no se habilita
el visor de la maniobra mediante el lanzador.

## Ejecutar desde la raíz de RoboPenalty-AI-Complete

Usa el entorno privado ya preparado para 4B.1; no instala nada ni requiere los
104 recursos del juego. Deploy se abre solo para lectura desde la ruta indicada.

```powershell
.\scripts\probar_preparacion_4b2.ps1 -DeployPath "..\RoboNaldo_Deploy"
```

Primero ejecuta una referencia 4B.1 nueva sin cambiar su implementación y exige
el hash físico histórico exacto. Después realiza tres ensayos residuales. Si
aparece una interrupción de seguridad no repite esa maniobra. Si el ensayo es
seguro pero falla movimiento o recuperación, completa las tres repeticiones.

Código Python 0: criterios físicos y de recuperación aprobados. Código 2:
ensayo no aprobado; no significa necesariamente que el robot haya caído.
Las carpetas de salida son nuevas y nunca se sobrescriben. `-Salida` permite
elegir una carpeta nueva y `-Python` otro intérprete compatible.

`trace.npz` guarda estados qpos/qvel y tiempo (5001 muestras), referencia original
de política, residual solicitado, referencia final limitada, torque solicitado,
control y torque articular aplicado (5000 muestras previas a integración),
observaciones y acciones originales de política (500 decisiones). Los contactos,
fuerzas y distancias se guardan en JSONL. `summary.json` conserva límites,
umbrales, hashes, métricas y la comparación posterior con 4B.1.

La habilitación del visor exige `report.json` aprobado con tres repeticiones
idénticas y la misma firma de código físico. Forma de uso, únicamente cuando
una ejecución haya sido aprobada:

```powershell
.\scripts\probar_preparacion_4b2.ps1 -DeployPath "..\RoboNaldo_Deploy" -Viewer -Validacion ".\validation\keeper_residual4b2\UNA_EJECUCION_APROBADA"
```

No hay bypass de amplitud, ganancias ni autorización del visor. La ejecución
inicial **no aprobó recuperación**, por lo que esta ventana no está habilitada.
No se ha evaluado naturalidad visual. El visor original de equilibrio sigue
disponible sin modificar:

```powershell
.\scripts\probar_equilibrio_4b.ps1 -DeployPath "..\RoboNaldo_Deploy" -Viewer -Repeticiones 1
```

## Tests

```powershell
$python = (Resolve-Path .\validation\keeper_balance4b\.venv\Scripts\python.exe).Path
Push-Location .\app\RoboPenalty
try { & $python -B -m unittest experiments.keeper_residual4b2.test_residual -v } finally { Pop-Location }
```

Los tests usan ejemplos sintéticos para comprobar rechazos; no presentan esos
ejemplos como resultados físicos. Los resultados reales están en RESULTADOS.md.
