# HU-13 — Comparación y regresión de versiones de reglas

## Objetivo

Permitir al desarrollador experimentar con una nueva versión de las reglas R01–R11 **antes de publicarla**, utilizando exactamente los mismos hechos de entrada y manteniendo el contrato original de Laravel.

El comparador no edita `data/rules.json`, no modifica el motor público, no fusiona ramas ni tiene acceso a los precios de supermercados. Las reglas se evalúan mediante `run_inference_with_rules`: la misma inferencia, clasificador, resolución de conflictos e índice del servicio vigente, pero con conjuntos aislados de reglas.

## Contrato opcional

`POST /api/v1/rule-regression` admite:

```json
{
  "anterior": {
    "etiqueta": "v1",
    "reglas": [/* objetos ProductionRule válidos */]
  },
  "propuesta": {
    "etiqueta": "v2-prueba",
    "reglas": [/* objetos ProductionRule válidos */]
  },
  "escenarios": [
    {
      "nombre": "Compra ideal",
      "hechos": { "request_id": "...", "alternativa_id": "...", "...": "14 campos" }
    }
  ]
}
```

Las reglas usan exactamente el esquema de `data/rules.json`; los hechos siguen teniendo los mismos 14 campos de `/recommend`. Para obtener la versión actual, consulta `GET /api/v1/knowledge`. Se aceptan entre 1 y 32 reglas por snapshot y entre 1 y 10 escenarios. IDs duplicados, hechos desconocidos, comparaciones booleanas de hechos numéricos y estructuras incompletas reciben HTTP 422.

**Las etiquetas de versión se proporcionan por el solicitante** y no se consideran autenticadas. La respuesta incluye dos huellas SHA-256 de las reglas normalizadas que permiten distinguir las bases efectivamente evaluadas, aunque las etiquetas sean iguales o se modifique el orden de sus elementos.

## Cambios observados

La respuesta presenta las reglas **agregadas, retiradas y modificadas**, y por cada escenario:

- Nivel anterior y propuesto.
- Regla ganadora anterior y propuesta.
- Reglas activadas con cada versión.
- Explicación de la decisión con cada versión.
- Indicadores separados de cambios de nivel, ganadora, activaciones y explicación.
- Índice auxiliar de ambas ejecuciones.
- Señal **regresión crítica**: una recomendación de riesgo (`NO_RECOMENDABLE`, con R01–R05 activa) que pasaría a `BUENA` o `EXCELENTE` con las reglas propuestas.

El motor **no bloquea ni publica automáticamente** versiones: informa de la regresión para que se revise el cambio.

## Ejemplo reproducible

R06 tiene prioridad 5 y R07 prioridad 6. En el escenario sintético “Compra ideal” ambas se activan y R06 gana con resultado `EXCELENTE`.

Si únicamente cambiamos la prioridad de R06 a 7 **en memoria**, R07 gana con resultado `BUENA`. El índice auxiliar no cambia porque los hechos y sus pesos siguen siendo los mismos.

Una prueba de riesgo modifica la prioridad de R02 en una compra con un producto esencial faltante y dos supermercados con ahorro alto. Si R08 llegase a ganar mientras R02 permanece activada, el sistema señala una **regresión crítica**.

## Interfaz Streamlit

En **Base de conocimiento → Comparador de versiones de reglas**, selecciona **Cargar reglas actuales para comparar**, elige la regla y ajusta una prioridad de prueba. Pulsa **Comparar versiones de reglas**.

La interfaz no incluye edición libre del archivo de producción. Su objetivo es **simular de forma segura** diferencias y visualizar su impacto sobre los nueve escenarios sintéticos precargados. El informe JSON puede descargarse para inspección técnica. Para comparar dos snapshots arbitrarios se dispone de la ruta API opcional.

## Alcance y pruebas

La muestra solo demuestra el comportamiento frente a los casos suministrados. Que no existan cambios de dictamen **no garantiza** equivalencia universal de las bases: otras combinaciones de hechos podrían activarlas de forma diferente. Al mantener constantes los hechos y el índice auxiliar, el comparador aísla diferencias **de reglas**, no de versiones de pesos o clasificadores.

```bash
python -m pytest -q tests/test_rule_regression.py
python -m pytest -q
ruff check app demo tests
```

Las pruebas comprueban igualdad entre snapshots idénticos, cambios de prioridad, cambios solo textuales, reglas agregadas o retiradas, regresiones críticas, huellas deterministas, validación 422, seguridad `X-API-Key` y ejecución desde Streamlit hacia FastAPI con ASGITransport.

No se modifica `develop` de Steven ni las rutas existentes del backend.
