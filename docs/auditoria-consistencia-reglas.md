# Auditoría de consistencia del sistema experto — HU-11

## Objetivo

Identificar problemas de diseño en la base de conocimiento **antes** de modificar `data/rules.json`. La auditoría es de solo lectura y no cambia la inferencia. Trabaja exclusivamente en Python; Laravel sigue usando `POST /api/v1/recommend` sin cambios.

La auditoría tiene dos capas:

1. **Análisis estructural:** compara pares de condiciones y la prioridad configurada; detecta identificadores repetidos, reglas con condiciones idénticas, conclusiones divergentes, reglas que nunca pueden ganar porque otra más general tiene prioridad, contradicciones lógicas conocidas y hechos numéricos usados como booleanos.
2. **Evaluación de clases representativas:** construye entradas sintéticas válidas alrededor de los clasificadores y registra dónde se activan las reglas juntas. Los resultados muestran un ejemplo reproducible y quién gana por prioridad.

## Clases representativas

Se emplean los valores representativos siguientes (no son datos de supermercados reales):

| Dimensión | Clases ensayadas |
|---|---|
| Presupuesto | Dentro, excedido hasta 10 %, excedido más de 10 % |
| Ahorro | Bajo, medio, alto |
| Distancia adicional | Corta, media, lejana |
| Tiempo | Bajo, medio, alto |
| Productos | Todos, faltan opcionales, faltan esenciales, faltan ambos, sin esenciales |
| Supermercados | 1, 2, 3 |
| Promociones | No, sí |

El producto cartesiano da **2430 escenarios sintéticos**. Cada entrada pasa por `RecommendationRequest` y `derive_facts` igual que el motor. Se comprueban todas las combinaciones de estas *clases*, pero no todos los números, listas reales ni futuras extensiones del clasificador.

## Tipos de hallazgos

| Código | Interpretación |
|---|---|
| `ID_DUPLICADO` | Dos o más reglas usan el mismo identificador (el cargador de reglas ya rechaza esta situación) |
| `CONDICIONES_INCOMPATIBLES` | La regla pide estados simultáneamente imposibles bajo los clasificadores actuales |
| `HECHO_NO_BOOLEANO` | La regla compara con verdadero/falso un hecho derivado que realmente es numérico |
| `CONDICIONES_DUPLICADAS` | Dos reglas usan exactamente el mismo conjunto de condiciones |
| `SALIDAS_DIVERGENTES` | Dos reglas tienen condiciones idénticas pero respuestas/acciones distintas |
| `REGLA_SOMBREADA` | Una regla de mayor prioridad tiene todas sus condiciones incluidas en una regla más específica; esta última no puede ganar |
| `SIN_ACTIVACION_EN_MUESTRA` | No se observaron activaciones entre los casos sintéticos ensayados; **no prueba que la regla sea imposible** |

Los hallazgos informan; no reescriben ni desactivan reglas. La semántica de `CONDICIONES_INCOMPATIBLES` se basa en particiones mutuamente excluyentes de presupuesto, ahorro, distancia, tiempo y supermercados, además de las relaciones de disponibilidad válidas según el contrato.

### Solapamientos y conflictos controlados

Un solapamiento indica que dos reglas pueden activarse en el mismo caso sintético. **No es necesariamente un error.** Por ejemplo, R06 y R07 pueden estar activas a la vez y R06 gana por prioridad; R03 y R04 tienen la misma prioridad y gana R03 por orden alfabético del ID. La respuesta incluye el par, ambos niveles, la regla que gana, el número de coincidencias *en la muestra* y un ejemplo de entrada reproducible.

Si las dos reglas expresan niveles distintos, se identifica el conflicto de nivel, aunque la resolución siga siendo determinista. El número de coincidencias no representa la frecuencia de sucesos de compras reales.

## API y seguridad

`GET /api/v1/rule-audit` devuelve una respuesta JSON con:

- `version_reglas`, `reglas_evaluadas` y `escenarios_sinteticos`;
- `cobertura`, `hallazgos` y `solapamientos`;
- `resumen` y `limitaciones`.

Usa la misma protección opcional `X-API-Key` que `/knowledge`. No acepta reglas externas por HTTP, ni modifica archivos o configuraciones, ni altera el contrato de recomendación.

El panel se encuentra en la pestaña **Base de conocimiento** de Streamlit, bajo el botón **Auditar base de conocimiento**. Permite descargar la evidencia en JSON.

## Cómo verificar

```bash
python -m pytest -q tests/test_rule_auditor.py
python -m pytest -q
ruff check app demo tests
```

Las pruebas incluyen reglas artificiales duplicadas, contradictorias o sombreadas, comprobación de solapamientos reales de R01–R08, determinismo, ejemplos reproducibles, autenticación HTTP y la interfaz Streamlit. Ningún test modifica la base de producción.

## Límites

Este verificador no es un demostrador formal de satisfacibilidad universal. Una ausencia de activación debe interpretarse como **ausencia de cobertura de muestra**. Los hallazgos estructurales basados en igualdad, inclusión de condiciones o contradicciones de particiones sí representan relaciones lógicas de las reglas actuales. Al añadir hechos derivados o cambiar umbrales, deben revisarse las clases representativas y las particiones.

No se usan precios reales, scraping, aprendizaje automático ni evaluaciones de especialistas externos.
