# Análisis de sensibilidad del sistema experto

## Propósito

Una recomendación basada en reglas no debe describirse como robusta únicamente porque un caso favorable produjo el resultado esperado. Este módulo somete la misma alternativa a modificaciones **hipotéticas y deterministas** para comprobar si su conclusión cambia ante variaciones pequeñas y comprensibles.

El módulo reutiliza `RecommendationRequest`, el motor R01–R08 y el índice de conveniencia existentes. No modifica la entrada ni la salida de `POST /api/v1/recommend`.

## Contrato

`POST /api/v1/sensitivity` recibe:

```json
{
  "alternativa": {
    "request_id": "caso-001",
    "alternativa_id": "sucursal-1",
    "costo_total": 42.5,
    "presupuesto": 50,
    "ahorro": 11.25,
    "distancia_km": 2.3,
    "distancia_adicional_km": 0.8,
    "tiempo_estimado_min": 12,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": true
  }
}
```

Devuelve `escenario_base`, `escenarios`, `cantidad_decisiones_distintas`, `interpretacion` y `advertencias`. Cada escenario conserva el resultado experto completo, la traza, los cambios de entrada y la diferencia del índice.

## Escenarios definidos

| Escenario | Cambio | Qué permite estudiar |
|---|---|---|
| Precio +5 % | Incrementa el costo; recalcula ahorro manteniendo una referencia fija | Sensibilidad presupuestaria |
| Precio +10 % | Igual, con mayor aumento | Proximidad al umbral crítico R01 |
| Distancia +2 km | Incrementa distancia total y distancia adicional | Cambios de la clasificación de cercanía |
| Tiempo +15 min | Aumenta el tiempo, sin asumir más distancia | Variación de conveniencia temporal |
| Sin promociones | Desactiva el indicador, si inicialmente era verdadero | Dependencia de beneficios promocionales |
| Falta un esencial | Resta uno a esenciales disponibles y productos disponibles | Riesgo de falta de cobertura esencial |

Los escenarios que no corresponden a los hechos iniciales no se generan. Cada variación se valida con el mismo modelo Pydantic que una recomendación pública.

## Definición de cambio

Se contabiliza un cambio cuando varía el `nivel_recomendacion` **o** la `winning_rule`. Una variación del índice auxiliar por sí sola no implica un cambio de decisión.

La salida no expresa probabilidades, incertidumbre estadística ni predicciones de fluctuaciones de mercado: solo respuestas del motor ante un conjunto concreto de supuestos.

## Pruebas automatizadas

```bash
python -m pytest -q tests/test_robustness_and_sensitivity.py
python -m pytest -q tests/test_rule_boundaries.py
python -m pytest -q
ruff check app demo tests
```

Además se prueban preguntas ambiguas del chatbot, explicaciones ligadas a la regla negativa ganadora, rechazo de entradas no finitas, límites exactos de ahorro/presupuesto/distancia/tiempo y 100 alternativas seudoaleatorias reproducibles con semilla fija.

## Limitaciones y oportunidades futuras

- El análisis modifica un factor principal cada vez; no estudia combinaciones ni distribuciones probabilísticas.
- El precio de referencia se mantiene fijo al recalcular el ahorro; esta hipótesis se documenta para que el usuario no confunda la simulación con datos comerciales.
- El análisis recibe exclusivamente los hechos del contrato de recomendación. El backend que los proporciona es responsable de obtener y preparar los valores; este módulo no consulta catálogos, establecimientos ni fuentes externas.
- La evaluación del motor se basa en pruebas internas reproducibles, casos límite, conflictos entre reglas y sensibilidad. Superar las pruebas verifica el comportamiento respecto a los criterios programados, no su precisión comercial general.
