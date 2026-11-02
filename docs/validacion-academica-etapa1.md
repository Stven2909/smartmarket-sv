# Matriz de validación académica — etapa 1

Esta matriz reúne comprobaciones internas reproducibles de la lógica de reglas. Los escenarios de demostración son sintéticos; los casos provenientes de observaciones reales capturadas manualmente deben identificarse con su fuente y fecha en un registro separado. No se requiere evaluación por especialistas externos ni se afirma exactitud comercial.

## Política de compatibilidad

- No se cambia la ruta `POST /api/v1/recommend`, la estructura de respuesta, los niveles ni los identificadores R01-R08.
- Se admite `productos_esenciales_totales = 0`, siempre con `productos_esenciales_disponibles = 0`. La cobertura de esenciales se define como 100 % en este caso.
- Se rechazan conteos globales, esenciales u opcionales inconsistentes.
- R06 conserva el nivel EXCELENTE cuando cumple sus cinco condiciones, pero no afirma que la lista completa esté disponible: pueden faltar productos opcionales.
- La priorización entre alternativas sigue siendo responsabilidad de Laravel; este cambio no modifica sus pesos ni su score.

## Casos revisados

| Caso | Resultado esperado | Justificación |
|---|---|---|
| Compra ideal y lista completa | R06, EXCELENTE | Presupuesto, esenciales, distancia, tiempo y una parada favorables |
| Compra próxima, falta opcional | R06, EXCELENTE; advertir opcionales | Un esencial completo no implica lista completa |
| Sin productos esenciales marcados | R06 si las otras condiciones se cumplen | No hay esenciales obligatorios pendientes |
| Esenciales totales superiores al total | HTTP 422 | Conteo imposible |
| Esenciales disponibles superiores al disponible | HTTP 422 | Conteo imposible |
| Opcionales disponibles superiores a opcionales totales | HTTP 422 | Conteo imposible |
| Esenciales negativos | HTTP 422 | Conteo imposible |
| Ninguna regla activa | NO_RECOMENDABLE provisional, sin regla ganadora | Política heredada; pendiente de revisión académica |

## Riesgos que siguen abiertos

1. El exceso presupuestario entre 0 y 10 % no tiene una regla específica.
2. La conclusión por defecto es NO_RECOMENDABLE, incluso para casos intermedios.
3. Laravel todavía envía alternativas individuales de una sola sucursal, por lo que R05 y R08 quedan fuera del flujo real.
4. Los umbrales y los pesos del índice son supuestos del MVP: requieren análisis de sensibilidad y justificación.
5. El motor evalúa reglas en una pasada, no encadena hechos inferidos de reglas previas.

## Ejecución

```powershell
python -m pytest -q
python -m pytest -q tests/test_validation_improvements.py
```

Antes de integrar, comprobar además el payload real de Laravel en `/api/v1/recommend` y el caso sin esenciales desde Streamlit.
