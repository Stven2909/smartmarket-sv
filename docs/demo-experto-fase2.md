# SmartMarket SV — Laboratorio experto (fase 2)

## Objetivo

Mostrar y justificar decisiones de compra de un **sistema experto basado en ocho reglas de producción**. El motor Python es un servicio autónomo: no requiere Laravel o React para ejecutar su inferencia, su chatbot ni sus pruebas académicas.

Esta fase agrega una demostración visual, una comparación opcional de varias alternativas y la consulta de parámetros de la base de conocimiento, **sin cambiar el contrato original** de `POST /api/v1/recommend`.

## Componentes

| Vista | Función | Evidencia |
|---|---|---|
| Laboratorio | Edita hechos de los escenarios precargados | Dictamen, acción y explicación |
| Auditoría | Explica por qué una regla coincidió o no | Traza de condiciones de las 8 reglas |
| Índice auxiliar | Desglosa las cinco contribuciones ponderadas | Pesos, normalizaciones y puntos |
| Comparador | Ordena de 2 a 10 alternativas mediante reglas y desempates | Ranking y justificación por alternativa |
| Base de conocimiento | Consulta la fuente real de reglas y pesos por HTTP | R01–R08, prioridades, umbrales y pesos |
| Chatbot | Responde sobre la recomendación ya recibida | Explicaciones deterministas |

## API

### Endpoints existentes — sin cambios

- `POST /api/v1/recommend`: mismos 14 hechos de entrada, 16 campos de respuesta, identificación de reglas y explicación.
- `POST /api/v1/chat`: explicaciones sobre una recomendación ya generada.
- `GET /health`: salud del servicio.

### Endpoints nuevos — opcionales

**`POST /api/v1/compare`**

```json
{
  "alternativas": [
    {
      "request_id": "comparacion-a",
      "alternativa_id": "tienda-a",
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
    },
    {
      "request_id": "comparacion-b",
      "alternativa_id": "tienda-b",
      "costo_total": 56,
      "presupuesto": 50,
      "ahorro": 20,
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
  ]
}
```

Requiere entre 2 y 10 alternativas, IDs distintos y el mismo presupuesto. Devuelve `mejor_alternativa_id`, `criterio_orden`, `ranking` (cada entrada con la respuesta completa de `/recommend`) y `advertencias`. Las entradas mal formadas reciben HTTP 422.

Orden determinista: (1) EXCELENTE, (2) BUENA, (3) NO_RECOMENDABLE provisional, (4) NO_RECOMENDABLE por riesgo crítico. Dentro de cada grupo: mayor índice de conveniencia, menor costo y finalmente ID alfabético. **El índice no revoca reglas críticas**. Una posición 1 no implica que la compra sea segura o favorable cuando todas las opciones son malas.

**`GET /api/v1/knowledge`**

Devuelve en modo lectura los ocho objetos de reglas, sus condiciones, los umbrales, los pesos y las versiones correspondientes. Al igual que los demás endpoints protegidos, exige `X-API-Key` si `SMARTMARKET_API_KEY` está configurada.

## Ejecución local en Windows

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

En otra terminal:

```powershell
python -m streamlit run demo/streamlit_app.py
```

El laboratorio utiliza `http://127.0.0.1:8001` por defecto. Se puede cambiar en la barra lateral o mediante `SMARTMARKET_API_URL`. La demo de comparación necesita que FastAPI tenga esta fase desplegada.

## Validación

```powershell
ruff check app demo tests
python -m pytest -q
```

Las pruebas cubren contrato anterior, determinismo y conflictos, rankings, HTTP 422, X-API-Key y arranque de las tres vistas con el entorno de pruebas de Streamlit. Las pruebas ASGI no requieren desplegar Laravel, Render ni conectar bases de datos.

## Limitaciones académicas

Este es un motor de producción determinista que evalúa una pasada de reglas, no aprendizaje automático ni encadenamiento iterativo de hechos derivados. El ranking es una función de comparación definida, no una probabilidad ni un modelo entrenado. Los umbrales y los pesos requieren validación de expertos externos para extrapolar a decisiones reales. Las reglas R05 y R08 se pueden demostrar con escenarios multitienda, aunque el flujo actual de Laravel entregue alternativas individuales.
