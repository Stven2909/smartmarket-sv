# HU-24 — Inferencia opcional de varias alternativas (solo Python)

## Qué hace y qué NO hace

`POST /api/v1/recommend/batch` permite al backend enviar de 1 a 50 alternativas en una solicitud HTTP autenticada y recibir **una inferencia independiente por alternativa**, sin hacer 1 llamada de red por cada supermercado.

El servicio **no calcula precios, no compara ofertas, no reordena opciones, no elige una sucursal ganadora ni modifica datos de Laravel**. Solo realiza exactamente el mismo trabajo que `POST /api/v1/recommend` para cada elemento, dentro de una solicitud.

La nueva ruta es opcional: `POST /api/v1/recommend` permanece inalterada, y Laravel puede seguir usándola mientras decide si implementa el envío por lotes. Tampoco se cambia `develop` ni las ramas del equipo.

## Solicitud

```http
POST /api/v1/recommend/batch
X-API-Key: <secreto compartido entre servidores>
Content-Type: application/json
Accept: application/json
```

```json
{
  "alternativas": [
    {
      "request_id": "lista-42-sucursal-1",
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
  ]
}
```

El array debe contener entre **1 y 50** elementos, todos con el mismo contrato existente de 14 campos. Cada objeto debe tener un `request_id` distinto; dos objetos con el mismo identificador producen 422. No se exige que cada `alternativa_id` sea distinto: una misma tienda podría evaluarse en escenarios diferentes con IDs de solicitud propios.

## Respuesta

```json
{
  "resultados": [
    {
      "request_id": "lista-42-sucursal-1",
      "nivel_recomendacion": "EXCELENTE",
      "...": "los otros 14 campos habituales de RecommendationResponse"
    }
  ]
}
```

**El bloque anterior es ilustrativo, no una respuesta literal válida** (los puntos suspensivos indican los campos restantes). Cada elemento contiene los mismos **16 campos** que el endpoint individual, incluida la regla ganadora, la traza y el índice auxiliar. El orden de `resultados` es exactamente el orden de `alternativas`. Las respuestas correctas incluyen la cabecera `X-Expert-Rules-SHA256` de las reglas utilizadas, y las cabeceras `Cache-Control: no-store` y `X-Content-Type-Options: nosniff`.

**Atomicidad de validación:** si falta un campo, existe duplicidad de `request_id`, se excede el límite o se envía una alternativa inválida, se devuelve HTTP 422 para toda la petición, sin resultados parciales. Si la base de reglas falla se devuelve 503 genérico. El lote no genera escrituras persistentes, por lo que un rechazo no deja operaciones parciales en una base de datos.

El conjunto está sujeto a la misma autenticación `X-API-Key` que las otras rutas de `/api/v1/*`.

## Beneficios y límites

Una solicitud para todas las alternativas reduce la cantidad de **viajes HTTP** entre Laravel y Python. **No implica** un aumento medido del rendimiento del motor, pues cada alternativa aún se evalúa por separado. La mejora en latencia total depende de cuántas alternativas envíe Laravel, la conexión a Render, sus reintentos y la latencia de arranque.

El uso por Laravel requiere que el compañero implemente voluntariamente el envío de `alternativas` y consuma `resultados`; es una mejora para coordinación futura, no un cambio impuesto. Para cantidades mayores de 50, Laravel debe dividir en varios lotes o mantener las llamadas individuales.

## Verificaciones

- `tests/test_batch_recommendation.py` compara las respuestas batch vs. endpoint individual con casos R06, R02 y R01.
- Verifica límites, identificación única de cada solicitud, errores 422/503, protección API key y huella de reglas.
- La CI continúa probando compatibilidad de los 14/16 campos del endpoint original sin modificar `develop`.
