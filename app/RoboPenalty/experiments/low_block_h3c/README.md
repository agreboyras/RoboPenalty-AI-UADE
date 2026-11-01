# Hito 3C: ensayo de bloqueo bajo activo

**Resultado: BLOQUEADO para el objetivo de atajada activa.** La variante se ejecuta físicamente y mueve las articulaciones, pero empeora el contacto del centro-izquierda y sigue siendo gol. No se recomienda integrarla. La calibración se detuvo sin aumentar amplitudes.

## Ver el resultado real

Desde la raíz de RoboPenalty-AI-Complete:

```powershell
.\scripts\probar_bloqueo_bajo_h3c.ps1 -Modo active -Amplitud 0.04 -Viewer -Camara goal
.\scripts\probar_bloqueo_bajo_h3c.ps1 -Modo passive -Viewer -Camara goal
```

Ejecutar uno por vez. Ambos usan `left_near_b060`. La maniobra es pequeña; no hay zambullida. La pelota toca la pierna y termina entrando. El visor cierra al terminar 14 s simulados y la pausa final; cerrarlo antes deja una evaluación incompleta. Repetir un comando crea una carpeta fechada nueva en `validation/low_block_h3c/`. Los resultados definitivos aparecen en consola y `interception.json`; el marcador visual no es un evaluador independiente de este ensayo.

Control central, con **los mismos parámetros y regla**:

```powershell
.\scripts\probar_bloqueo_bajo_h3c.ps1 -Modo active -Amplitud 0.04 -Accion center -Viewer -Camara goal
```

El central no debe activar el residual: queda atajado pasivamente, como en 3A/3B. No interpretar esto como éxito de la maniobra activa.

Para headless, omitir `-Viewer`. Cámaras: goal, behind, execution y overview. El lanzador reutiliza los dos entornos privados y las importaciones externas existentes de H1/4B, sin descargar, instalar o copiar checkpoints. La referencia apartada validada se resuelve desde H3B. No es un instalador público autónomo.

## Arquitectura

- `run.py`: bucle privado derivado de código propio H1, reutilizando composición, política auxiliar, inicialización FreeKick, caps y registrador H3A. Fue necesario aislar el bucle para permitir una caída física posterior a la activación sin el anclaje ni la interrupción de equilibrio de H1. Los archivos históricos no se modifican.
- Equilibrio principal intacto: checkpoint, contrato de observaciones, normalizador, memoria recurrente y ganancias originales. El estado recurrente se reinicia al comenzar y después evoluciona normalmente. Un solo PD propietario de los torques recibe `referencia de política + residual`. No existe otro controlador de torques ni escritura de pelvis durante la integración.
- `maneuver.py`: no recibe preset, resultados de referencia o trazas futuras. Usa solo tiempo actual, posición y velocidad observadas. Dos observaciones consecutivas a 50 Hz deben indicar pelota entrante, Vx>=0.8 m/s, altura <=0.25 m y proyección horizontal en X4.1 dentro de Y=[0.18,0.50], con ETA<=1.5 s. Es una condición local experimental de activación, no un agente completo de selección de atajadas.
- Residual evaluado: cadera roll derecha -0.04 rad, tobillo roll derecho +0.04 rad. Rampa quíntica 0.30 s; mantenimiento hasta observar pelota más allá de X4.4, rebote o límite relativo de 1.8 s desde detección; retirada suave 0.35 s. No hay temporizador absoluto del preset.
- El protocolo contemplaba amplitud 0.08 rad como posible ensayo posterior, pero **no fue ejecutada ni validada y no se recomienda utilizarla**. Se detuvo la búsqueda en 0.04 por ausencia de beneficio útil. No cambiar la amplitud para reproducir los resultados documentados.
- Preparación exige equilibrio H1; tras activación se permiten inclinación y caída, conservando límites físicos. Aceptación: 20 rad/s de velocidad articular, 20 mm de penetración del arquero, 0.03 rad de exceso articular, caps efectivos y saturación continua <0.10 s. Interrupciones de seguridad: 40 rad/s, 30 mm, 0.10 rad o saturación >=0.50 s, además de NaN/fuerzas externas. La caída no se corrige con posiciones o fuerzas artificiales.

## Registros y límites de interpretación

`commands` en `maneuver.npz`: tiempo, referencia original 29, residual 29, referencia final 29, articulaciones reales 29 y velocidades 29. `points` guarda pelvis, rodilla derecha y tobillo derecho; `world` conserva estados completos. `trace.npz` mantiene el esquema H1 para comparación exacta. `observations.json` registra cada evidencia y predicción local. Fuerzas, impulsos, trayectorias y límites se guardan en `ball_keeper_contacts.json` e `interception.json`.

Las rampas nominales evaluadas son suaves y el residual vuelve a cero. Eso no acredita recuperación de la postura original ni seguridad para otras trayectorias o cancelaciones tempranas no ensayadas. El control central solo valida la no activación y conservación de ese nominal.

Consultar [RESULTADOS.md](RESULTADOS.md). Todo el resultado negativo se conserva; no se integra en los modos públicos ni se continúa hacia otra estrategia.
