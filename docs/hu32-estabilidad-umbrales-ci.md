# HU-32 — Estabilidad numérica de umbrales y puertas de regresión

**Alcance:** exclusivamente el motor Python y la integración continua de nuestro fork.
No se modifican Laravel, React, `develop`, Render, Streamlit ni los pesos de producción.
El contrato HTTP conserva 14 hechos de entrada y 16 campos superiores de salida.

## Hallazgo 1: redondeo visual frente a precisión matemática

Las reglas ponderadas R14, R15 y R16 necesitan umbrales de 75, 50 y 60 puntos.
La salida pública muestra dos decimales, pero las condiciones deben usar el índice
sin redondear. Hay dos riesgos diferentes:

- **Falso positivo:** 74.99825 se muestra como 75.00, pero no satisface R14;
  49.998 se muestra como 50.00, pero no satisface R15; 59.99625 se muestra
  como 60.00, pero no satisface R16.
- **Falso negativo numérico:** la combinación de R14 con 14.5 de ahorro, 100 %
  de disponibilidad, 6 km adicionales, 35 minutos y sin promociones equivale
  matemáticamente a 75, pero las operaciones binarias pueden producir
  `74.99999999999999`.

La corrección centraliza la comparación interna en
`meets_convenience_threshold()`: acepta el valor que supera el umbral
o difiere de él en un máximo absoluto de `1e-12` debido a precisión de coma
flotante. **No utiliza redondeo a dos decimales para decidir.**
La salida redondeada al público no cambia.

Los tests reproducen ambos lados de los umbrales R14, R15 y R16, e incluyen
`math.nextafter()` para comprobar el caso binario inmediatamente inferior.
Se versiona el ajuste semántico como `RULES_VERSION=1.3.2` y
`THRESHOLDS_VERSION=1.3.2`; no se modifica `data/rules.json`.

## Hallazgo 2: cobertura incompleta en la puerta de regresiones

`scripts/behavior_guard.py` solo consideraba críticas R01–R05, mientras que el
motor también protege mediante R09, R10 y R12. Se sincroniza el conjunto de
ocho IDs críticos. Ahora una pérdida de cualquiera de ellos debe bloquear una
regresión de código, incluso si el nuevo resultado sigue siendo
`NO_RECOMENDABLE`.

La descripción de la puerta de regresión de reglas también identifica los ocho
IDs, sin cambiar su lógica, que ya utilizaba el conjunto correcto.

## Hallazgo 3: los pushes directos omitían las puertas de regresión

Las dos puertas de regresión se ejecutaban solo cuando el evento era
`pull_request`; en `main`, un push directo pasaba de largo. Ahora se ejecutan
tanto en PR como en pushes a `main`. Para PR se compara contra el SHA de la
rama base; para push a `main`, contra `github.event.before`.

Este control compara cambios documentados y ejecutables aislados. No equivale
a demostrar que todas las decisiones comerciales sean correctas.

## Validación

```bash
pytest -q tests/test_weight_thresholds_hu32.py \
  tests/test_weighted_rules_hu30.py tests/test_behavior_guard.py
python -m scripts.calibrate_convenience_weights --with-grid
pytest -q
```

Se conserva el vector 35/25/20/15/5, el motor de 16 reglas y la prioridad de
protecciones críticas. **La calibración HU-31 no prueba una mejora comercial
real:** continúa basada en 3421 casos sintéticos sin etiquetas humanas.
