# Diagnóstico de recuperación extendida 4B.2

Protocolo establecido antes de ejecutar. No modifica 4B.1, 4B.2 ni sus resultados.

- Duración fija: 20 s, 10000 pasos de 2 ms y 1000 decisiones a 50 Hz.
- Residual original importado sin modificar: rodillas +0.02 rad, caderas pitch
  y tobillos pitch -0.01 rad; rampa 3–5 s, sostén 5–6 s, retorno 6–8 s.
- Desde 8 hasta 20 s: residual exactamente cero; no se repite la maniobra,
  no se reinicia memoria ni se corrige la base.
- Tres pares independientes baseline/residual. Baseline de locomoción física
  nula también dura 20 s, con exactamente la misma inicialización y límites.
- La comparación con baseline solo se hace después del ensayo; no alimenta la
  política ni modifica la consigna. Se registran errores de las 29 articulaciones.
- Ventana original 9–10 s: se conserva y reporta; no se reclasifica como PASS.
- Nueva ventana 18–20 s: error medio absoluto de cada una de las seis
  articulaciones intervenidas <=0.005 rad, error máximo absoluto también <=0.005
  rad, y error medio absoluto de altura de pelvis <=2 mm. El requisito de máximo
  es adicional y más estricto, no una relajación del umbral original.
- Se mantienen los criterios de flexión real originales (5.5–6 s), todos los
  límites y motivos de interrupción de 4B.2, sin cambios de ganancias, torque,
  geometría o amplitud. El baseline extendido también debe pasar seguridad.

Se exige identidad de todas las muestras de los primeros 10 s con los archivos
originales: estados, velocidades, observaciones, acciones, referencias y torques
cuando existen en ambos formatos. Una divergencia detiene el diagnóstico.

Los resultados no prueban convergencia asintótica: describen error medido durante
20 s. Se guardan errores medios, máximos y con signo por intervalos de un segundo,
valor final y cruces de cero (50 Hz, banda descriptiva de 1e-5 rad).

El visor solo se habilita si los tres pares son seguros, la recuperación extendida
aprueba y las tres trazas baseline y residual son respectivamente idénticas.
Si no aprueba, no se aumentan amplitudes ni se continúa ajustando residuales.

## Ejecución desde la raíz de RoboPenalty-AI-Complete

Reutiliza el entorno privado de 4B.1. No instala dependencias ni copia la política.

```powershell
.\scripts\probar_recuperacion_4b2.ps1 -DeployPath "..\RoboNaldo_Deploy"
```

El lanzador usa por defecto los resultados originales en
`validation/keeper_residual4b2/headless_01`. `-Original` permite indicar otra
carpeta de resultados originales equivalentes, nunca sustituir sus hashes.
`-Salida` permite elegir una carpeta nueva; no se sobrescriben ejecuciones.
Se interrumpe la serie completa si un baseline o residual infringe seguridad.
Por ello tres pares son el plan, no una promesa si el primer ensayo resulta inseguro.

Código Python 0: diagnóstico aprobado. Código 2: no aprobado, por criterio
de recuperación o seguridad. La ejecución inicial fue interrumpida y no aprobó.

Solo una ejecución aprobada permite abrir el visor privado:

```powershell
.\scripts\probar_recuperacion_4b2.ps1 -DeployPath "..\RoboNaldo_Deploy" -Viewer -Validacion ".\validation\keeper_recovery4b2\UNA_EJECUCION_APROBADA"
```

No hay ejecución aprobada actualmente. El visor de esta variante está bloqueado;
no hay flag para omitir los criterios. El visor 4B.1 sigue disponible sin cambios.

## Datos y tests

Cada par guarda `baseline/` y `residual/`, con estados, observaciones, acciones,
referencias, torques y contactos completos. Los informes conservan umbrales
fijados antes de ejecutar. El baseline solo se usa para evaluación posterior.
La ventana original no se sustituye por la nueva ni se declara aprobada.

`analyze.py` permite analizar un ensayo interrumpido sin integrar más física.
Su resultado es descriptivo y no cambia el informe de aceptación:

```powershell
$python = (Resolve-Path .\validation\keeper_balance4b\.venv\Scripts\python.exe).Path
Push-Location .\app\RoboPenalty
try {
  & $python -B -m experiments.keeper_recovery4b2.analyze --run "..\..\validation\keeper_recovery4b2\headless_01" --original-run "..\..\validation\keeper_residual4b2\headless_01" --output "..\..\validation\keeper_recovery4b2\NUEVO_POSTMORTEM"
  & $python -B -m unittest experiments.keeper_recovery4b2.test_recovery -v
} finally { Pop-Location }
```

El CSV de evolución contiene errores contra el baseline móvil a 50 Hz. Los NPZ
conservan los estados a 500 Hz. Las ventanas incompletas se marcan expresamente;
no se rellenan muestras ni se presentan promedios parciales como ventanas completas.
