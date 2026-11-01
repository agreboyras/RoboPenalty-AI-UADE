# Hito 2.5: maniobra desde el centro del arco

**Estado: PARCIAL.** La maniobra original funciona desde el centro con caída física, pero es lenta y alcanza el cajón posterior. Ninguna variante rápida probada supera todos los criterios. No hay selección autónoma ni atajada validada. No se avanzó al Hito 3.

## Visualizar

Desde PowerShell, situado en la raíz de `RoboPenalty-AI-Complete`:

```powershell
.\scripts\probar_centro_h25.ps1 -Variante original -Lado LEFT -Viewer
.\scripts\probar_centro_h25.ps1 -Variante original -Lado RIGHT -Viewer
```

Ejecutar un comando por vez. LEFT significa +Y mundial, izquierda del delantero; el arquero mira hacia -X. RIGHT es -Y. La cámara cercana se sitúa detrás del arco, por lo que la dirección de pantalla puede resultar opuesta a la del delantero.

El ensayo dura seis segundos simulados: equilibrio hasta t=2 s, transferencia, preparación, movimiento y caída. No hay recuperación. El visor cierra automáticamente al terminar; también puede cerrarse su ventana. Repetir el comando inicia un ensayo nuevo con salida fechada, sin sobrescribir resultados. No son los lanzadores públicos.

Para guardar capturas reales del renderizador MuJoCo, añadir `-Capturas`. Estas capturas añaden tiempo de presentación y no representan FPS del visor. Para headless, omitir `-Viewer`. Las salidas se guardan en `validation/keeper_center_h25/`, excluido de Git.

El lanzador reutiliza los dos entornos privados y las dependencias externas previamente verificadas de H1/H2; no instala ni descarga nada. No es un lanzador portátil para una instalación nueva. Mantiene las rutas relativas de esos experimentos y verifica los 104 SHA-256 antes de simular.

## Arquitectura

- `run.py`: carga una instancia privada del conductor H2 y sustituye exclusivamente sus enlaces locales de composición, selección de referencia, presentación y diagnóstico. No modifica H1/H2 ni sus módulos globales compartidos.
- Se reutiliza la composición H1 con raíz libre; pelvis inicial efectiva `(4.2, 0, 0.7794213197)` m, frente `(-1,0,0)`. La altura efectiva proviene de la colocación inicial de los pies del H1, no de imponer correcciones durante la integración.
- Hasta t=2 s, inferencia de equilibrio externa; después, referencias de maniobra. Un único PD envía los 29 torques del arquero a 500 Hz. La última inferencia ocurre a 1.98 s y la primera referencia propia coincide exactamente con ella. Ganancias y límites permanecen iguales.
- `trajectory.py`: original sin cambios, secuencias temporales comprimidas y una prueba de finalización. `fast_v1`, `fast_v2` y `fast` son variantes **rechazadas**, conservadas para reproducir el diagnóstico, no opciones recomendadas para atajar. `fast` es la última prueba con flexión de codo de finalización; no significa variante aprobada.
- `presentation.py`: reutiliza 7D sin modificarla y encuadra el centro del arco. Las capturas corresponden a estados físicos reales.
- `analyze.py`: análisis posterior de trazas; nunca suministra resultados futuros al controlador. Calcula tiempos de umbral, velocidades, trabajo articular y descomposición geométrica.
- `test_center.py`: regresiones de referencias, continuidad, tiempos, aislamiento de componentes y ausencia de orden FreeKick.

## Alcance del aislamiento de pelota

No se envía `CMD_FREEKICK`: el delantero permanece en el estado nominal FIXEDPOSE de su controlador existente. **Esto no garantiza estabilidad del delantero ni pelota inmóvil.** En los ensayos realizados el delantero cayó y la pelota se desplazó incidentalmente; no hubo contacto pelota-arquero ni contacto pie-pelota registrado. La causa exacta de ese desplazamiento incidental no quedó aislada. No se modificaron posiciones, velocidades, masa, colisiones o fuerzas de la pelota para ocultarlo.

Por ello, estos son ensayos sin tiro solicitado, no una validación completa de la condición «sin pelota activa». El campo antiguo `ball_active:false` de los primeros registros debe interpretarse únicamente como ausencia de orden de tiro; el código actual lo reemplaza por `commanded_shot:false` y una advertencia explícita. Los resultados anteriores no se reescriben.

## Diagnóstico reproducible

Desde `app/RoboPenalty`, con el Python privado MuJoCo del lanzador:

```powershell
& '..\..\validation\etapa2_final_20261030\RoboPenalty AI UADE\.venv\Scripts\python.exe' -X utf8 -B -m experiments.keeper_center_h25.analyze --run '..\..\validation\keeper_center_h25\NOMBRE_DEL_ENSAYO'
```

Genera `diagnosis.json` solamente si no existe. Las trazas contienen articulaciones, referencias, torques solicitados/enviados/reales, estados del mundo y salida de la política. `geometry.json` distingue contactos físicos de solapamientos visuales; `variant.json` documenta tiempos y hashes del adaptador. En los primeros registros originales, `real_knots` contenía un arreglo rápido no utilizado: la cronología ejecutada está correctamente registrada en `report.json/transitions`; el código actual corrige ese metadato.

Consultar [RESULTADOS.md](RESULTADOS.md) para mediciones, rechazos y limitaciones. No se modificaron inventarios históricos para incorporar este experimento privado.
