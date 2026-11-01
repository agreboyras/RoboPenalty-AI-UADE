# Hito 3B: cobertura pasiva del G1 libre

Experimento aislado de cinco tiros 8C sin maniobras ni planificación de atajada. Se reutiliza el conductor H1 y el registrador H3A, sin modificar sus archivos. La política externa de locomoción mantiene equilibrio con velocidad deseada cero, un único PD y raíz libre. «Pasivo» se refiere a la cobertura ante la pelota: el controlador de equilibrio sigue activo, pero no recibe observaciones de pelota ni el preset.

## Ejecutar y visualizar

Desde la raíz de RoboPenalty-AI-Complete:

```powershell
.\scripts\probar_cobertura_pasiva_h3b.ps1 -Accion left_near_b060 -Ubicacion centro -Referencia '.\validation\passive_coverage_h3b\reference_left_near_b060\interception.json' -Viewer -Camara goal
```

La referencia anterior existe en la instalación donde se validó H3B. Para crear otra pareja, usar una salida nueva:

```powershell
.\scripts\probar_cobertura_pasiva_h3b.ps1 -Accion right_inter_m080 -Ubicacion apartado -Salida '.\validation\passive_coverage_h3b\mi_referencia_derecha'
.\scripts\probar_cobertura_pasiva_h3b.ps1 -Accion right_inter_m080 -Ubicacion centro -Referencia '.\validation\passive_coverage_h3b\mi_referencia_derecha\interception.json' -Viewer -Camara goal
```

Acciones exactas disponibles: `center`, `left_near_b060`, `right_inter_m080`, `right_open_m100`, `right_corner_m140`. La referencia debe coincidir en acción y hash de calibración y estar apartada; se rechaza una pareja incompatible. Omitir `-Viewer` para headless. Añadir `-Capturas` para imágenes reales. Cámaras: goal, behind, execution, overview y follow.

Cada ensayo evalúa 14 segundos simulados, 7000 pasos. El visor cierra automáticamente después; cerrarlo antes deja un ensayo incompleto. Repetir un comando sin `-Salida` crea otra carpeta fechada sin sobrescribir. Los resultados definitivos se imprimen en consola y se guardan en `interception.json`; el marcador visual H1 no incorpora las atajadas de esta evaluación privada.

Se utilizan únicamente los entornos privados y dependencias externas ya presentes de H1/4B: el lanzador no descarga, instala ni copia checkpoints. No es un instalador autónomo público. Todas las salidas están bajo `validation/passive_coverage_h3b/`, excluido de Git.

## Clasificación y registros

- **ATAJADA:** prueba válida, contacto con desvío, referencia válida que fue gol, ausencia de gol durante la ventana completa. Una nueva atajada solo se considera demostrada tras repeticiones nominales verificadas.
- **CONTACTO SIN ATAJADA:** contacto y gol, en prueba válida.
- **SIN CONTACTO:** ninguna interacción física pelota-arquero en la ventana válida; no implica por sí sola gol ni tiro errado.
- **RESULTADO NO CONCLUYENTE:** prueba inválida/incompleta o evidencia insuficiente para atribuir una atajada.

Se conservan sin modificar las reglas de gol y clasificación de `phase4a`. H3B añade categorías de evidencia y verificaciones físicas del protocolo H3A: inclinación <15°, deriva <0.10 m, altura >=0.50 m, saturación continua <0.10 s, velocidad articular <=20 rad/s, penetración del arquero <=20 mm, exceso articular <=0.03 rad y caps de torque efectivos. Sin fuerzas externas ni contactos indebidos. El reporte legado H1 permanece separado y puede rechazar contactos esperados de pelota o su antiguo límite de penetración de 10 mm; no se reescribe.

`minimum_ball_keeper_distance` registra el mínimo global de superficies físicas mediante `mj_geomDistance`, con tiempo y cuerpo. `incoming_min_surface_gap_m` restringe el mínimo desde el impacto del delantero hasta el primer cruce X=5, con velocidad longitudinal positiva, para separar la aproximación de posteriores rebotes. Una distancia negativa describe solapamiento geométrico en el estado simulado, no un margen que deba cubrirse; la evidencia de contacto físico procede además de las fuerzas registradas por el solver.

`ball_keeper_contacts.json` contiene fuerza, estimación de impulso fuerza×dt, cuerpo y velocidades antes/después del paso. `trace.npz` conserva la traza H1 completa; `interception_trace.npz` registra cada paso de observación de contacto/distancia. No se añade integración ni se modifica el estado físico al observar.

`analyze.py` produce `coverage.json` y `coverage.csv`: parejas de referencia/centrado, reproducibilidad, trayectorias antes del contacto o gol y SHA-256 de conservación. `test_coverage.py` comprueba categorías, rechazo de referencias incompatibles y catálogo exacto. Consultar [RESULTADOS.md](RESULTADOS.md) para los resultados medidos y sus límites.
