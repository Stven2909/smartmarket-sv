# HU-14 — Puerta de regresiones en cambios de reglas

## Objetivo

Revisar automáticamente los cambios propuestos para `data/rules.json` en una solicitud de incorporación (pull request) a **este repositorio Python**, antes de aceptarlos. El control no edita `rules.json`, no consulta supermercados, no llama a Laravel ni depende de especialistas externos.

Se integra en el job `test` de `.github/workflows/ci.yml`, que ya ejecuta Ruff y Pytest. La nueva fase **Gate - Rule regressions on pull requests** se ejecuta en PR; si el contenido de `data/rules.json` no cambió, registra que no hay comparación pendiente y termina correctamente.

## Qué compara

1. Extrae la **versión base real del PR**, `github.event.pull_request.base.sha:data/rules.json`, mediante Git (nunca confunde una etiqueta de versión con los datos publicados).
2. Carga y valida ambas bases con `load_rules` y `RuleSnapshot`, usando el modelo de reglas del motor.
3. Evalúa las mismas **nueve alternativas sintéticas** de `data/scenarios.json` y **2430 escenarios de clases representativas** que emplea el auditor. Total: **2439 casos de prueba**.
4. Por cada caso utiliza la comparación HU-13, que reutiliza la inferencia vigente y su resolución por prioridad.
5. Escribe el resultado en GitHub Actions **Job Summary**, con métricas y hasta quince ejemplos de cambios. Opcionalmente genera un archivo JSON local para diagnóstico.

La evaluación informa cambios de nivel, regla ganadora, activaciones y explicación. Las entradas son sintéticas; la ausencia de diferencias no prueba equivalencia universal.

## Cuándo falla el control

El comando termina con código de salida **1** ante al menos una de las condiciones siguientes:

- **Regresión crítica:** una alternativa antes rechazada mediante R01–R05 pasa a `BUENA` o `EXCELENTE`.
- **Pérdida de protección:** una regla crítica R01–R05 que se activaba en la base anterior deja de activarse en la propuesta, incluso cuando el dictamen continúe siendo `NO_RECOMENDABLE`.
- **Hallazgos estructurales nuevos:** condiciones incompatibles, hechos numéricos usados como booleanos, duplicados, conclusiones divergentes para idénticas condiciones y reglas sombreadas sin posibilidad de ganar.

Los hallazgos estructurales ya presentes en la versión base se muestran al auditar, pero **no se consideran nuevos bloqueos** para permitir correcciones incrementales. Un cambio no crítico de prioridad o una modificación textual pueden aprobarse y aun así dejar las diferencias visibles.

Una entrada ilegible, JSON inválido o snapshot inconsistente produce código **2**, también fallido. Si las comprobaciones pasan, el código es **0**.

## Revisión desde GitHub

Al abrir un PR que modifica `data/rules.json`, consulta la pestaña **Checks / Actions → CI → test** y el resumen de la ejecución. Un error del control marca el job de CI como fallido.

**Importante:** el archivo de workflow por sí solo no configura una protección de rama en GitHub. Para impedir que un mantenedor fusione un PR cuyo CI falla, configurar la regla de protección de `main` en GitHub:

1. Ir a **Settings → Rules → Rulesets** (o **Branches**, según la interfaz).
2. Crear una regla para `main` que exija pull request y **status checks obligatorios**.
3. Seleccionar el check correspondiente al job **CI / test** y exigir que esté aprobado antes del merge.
4. Aplicar la protección a las personas que correspondan según los permisos del repositorio.

No deben utilizarse checks opcionales o condicionalmente omitidos como estado obligatorio. El job `test` sigue existiendo tanto si cambian reglas como si no.

El token usado por GitHub Actions mantiene permiso de **solo lectura** sobre el repositorio (`contents: read`). Se usa el evento `pull_request`, no `pull_request_target`, y no se transmiten secretos al script.

## Ejecución local

```bash
python -m scripts.check_rule_regression \
  --baseline /ruta/a/rules-anterior.json \
  --candidate data/rules.json \
  --scenarios data/scenarios.json \
  --json-output /tmp/comparacion-reglas.json
```

Se necesitan las dependencias definidas en `requirements.txt`. El script escribe un resumen legible, devuelve el código de salida apropiado y no escribe en la base de conocimiento. Si GitHub Actions define `GITHUB_STEP_SUMMARY`, también agrega allí el resultado.

Para ejecutar la prueba de aceptación:

```bash
python -m pytest -q tests/test_rule_change_gate.py
ruff check app demo tests
```

Las pruebas verifican aceptación de cambios benignos, rechazo de regresiones críticas, rechazo de pérdida silenciosa de R01, detección de contradicciones, rechazo de JSON ilegible y generación del resumen.

## Alcance

El control evalúa únicamente diferencias en el contenido de reglas con los **clasificadores y pesos del código candidato**. Si en el mismo PR se modifica `classifiers.py`, el script no compara automáticamente dos implementaciones diferentes del clasificador. Para cambios futuros de umbrales o semántica de hechos se requeriría una prueba de regresión de código adicional.

Tampoco publica ni revierte versiones, no modifica `develop`, no configura por sí mismo las reglas de protección de GitHub y no asegura cobertura de todos los valores posibles.
