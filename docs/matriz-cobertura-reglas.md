# Matriz de cobertura de las reglas

## Propósito

Comprobar que los escenarios de prueba ejercitan las once reglas del sistema experto y hacen visibles los conflictos y los casos sin regla. Esta es una **verificación funcional de escenarios sintéticos**, no una medición de precisión sobre compras reales.

La matriz histórica utiliza los nueve escenarios de `data/scenarios.json` y consulta `POST /api/v1/compare` para ejecutar el motor con los mismos hechos que procesa `POST /api/v1/recommend`. No recopila datos, no consulta Laravel y no agrega endpoints.

## Escenarios incluidos

| Escenario | Regla principal esperada | Resultado |
|---|---|---|
| Compra ideal | R06 | EXCELENTE |
| Presupuesto muy excedido | R01 | NO_RECOMENDABLE |
| Falta de productos esenciales | R02 | NO_RECOMENDABLE |
| Distancia lejana con ahorro bajo | R03 | NO_RECOMENDABLE |
| Tiempo alto con ahorro bajo | R04 | NO_RECOMENDABLE |
| Compra fragmentada | R05 | NO_RECOMENDABLE |
| Promociones relevantes | R07 | BUENA |
| Dos supermercados con ahorro alto | R08 | BUENA |
| Caso sin regla dominante | Ninguna | NO_RECOMENDABLE provisional |

**Casos complementarios HU-28:** `data/scenarios_hu28.json` contiene tres escenarios que ejercitan R09 (ningún producto), R10 (cobertura del 20 %) y R11 (compra completa equilibrada sin promoción). Se ejecutan por separado en tests y no se concatenan a una solicitud de comparación que limita a diez alternativas.

El escenario ideal activa tanto R06 como R07, y debe ganar R06 por su mayor prioridad. El caso sin regla dominante conserva `winning_rule = null`; no se inventa una regla adicional.

## Cómo leer los resultados

En la pestaña **Base de conocimiento**, utiliza el botón **Evaluar cobertura**. El panel muestra:

- **Activaciones:** cantidad de escenarios en los que se cumple la regla, aunque no resulte ganadora.
- **Victorias:** cantidad de escenarios donde la regla define el dictamen.
- **Escenarios con varias reglas activas:** comprueba la resolución de conflictos por prioridad.
- **Escenarios sin regla ganadora:** permite localizar el comportamiento provisional.
- **Reglas no activadas:** indica qué reglas no están cubiertas por este conjunto de ejemplos.

Los valores del panel se calculan a partir de la **traza completa devuelta por FastAPI**; Streamlit no ejecuta una segunda copia del motor.

## Casos frontera

La clasificación pública mantiene tres niveles: `EXCELENTE`, `BUENA` y `NO_RECOMENDABLE`. Cuando el costo excede el presupuesto hasta el 10 % y ninguna regla se activa, se conserva `NO_RECOMENDABLE` provisional y se indica explícitamente el exceso y la recomendación de ajustar la lista. Si el exceso supera el 10 %, R01 es crítica y determina el rechazo.

La distinción entre una conclusión provisional y un rechazo respaldado por R01–R05 es importante: el índice de conveniencia auxiliar no convierte ninguno de los dos en una regla favorable.

## Ejecución automatizada

```bash
python -m pytest -q tests/test_decision_coverage.py
python -m pytest -q
ruff check app demo tests
```

El objetivo es demostrar la **coherencia del software frente a casos definidos**. La matriz no certifica que los umbrales o las preferencias representen las decisiones de todos los compradores.


La matriz básica de nueve casos cubre las reglas históricas R01–R08. Los tres casos adicionales verifican las nuevas R09–R11 sin alterar los límites HTTP; el auditor `GET /api/v1/rule-audit` utiliza 3402 combinaciones representativas de las once reglas.
