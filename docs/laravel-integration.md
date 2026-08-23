# Integración futura con Laravel

## Responsabilidades

Laravel es el orquestador de SmartMarket SV:

1. Obtiene datos de usuarios, productos y alternativas.
2. Calcula o recibe costo, ahorro, disponibilidad, distancia y tiempo.
3. Envía únicamente hechos JSON validados.
4. Consume la recomendación y la explicación.
5. Continúa mostrando la optimización aunque el Sistema Experto no esté disponible.

Python es el motor experto:

1. Valida los hechos recibidos.
2. Deriva hechos internos.
3. Evalúa las reglas.
4. Resuelve conflictos.
5. Devuelve una recomendación determinista y explicable.

Python no consulta Laravel, PostgreSQL ni modelos internos de Laravel.

## Mapeo con el backend actual de `Desarrollo-Experto`

La versión actual de Laravel (`OptimizationService`) ya no calcula
`costo_combustible`. Calcula y devuelve, por alternativa:

```json
{
  "costo_total": 42.5,
  "beneficio_promociones": 3.25,
  "productos_esenciales_disponibles": 6,
  "productos_esenciales_totales": 6,
  "productos_opcionales_disponibles": 4,
  "productos_opcionales_totales": 4,
  "distancia_km": 2.3,
  "penalizacion_distancia": 0.0,
  "tiempo_minutos": 12.0,
  "costo_tiempo": 0.6,
  "score": 40.1
}
```

Ese es el resultado interno del optimizador, no el payload que debe enviarse
a Python. Laravel debe construir el contrato normalizado de esta forma:

| Campo Python | Construcción desde Laravel |
|---|---|
| `request_id` | `lista-{lista_id}-sucursal-{sucursal_id}` |
| `alternativa_id` | `sucursal-{sucursal_id}` |
| `costo_total` | `resultado.costo_total` |
| `presupuesto` | `lista.presupuesto`; si es `null`, omitir la llamada experta |
| `ahorro` | `max(0, costo_referencia - resultado.costo_total)` por alternativa |
| `distancia_km` | `resultado.distancia_km` |
| `distancia_adicional_km` | `resultado.distancia_km - distancia_minima` entre alternativas físicas |
| `tiempo_estimado_min` | `resultado.tiempo_minutos` |
| `productos_disponibles` | `productos_esenciales_disponibles + productos_opcionales_disponibles` |
| `productos_totales` | `productos_esenciales_totales + productos_opcionales_totales` |
| `productos_esenciales_disponibles` | `resultado.productos_esenciales_disponibles` |
| `productos_esenciales_totales` | `resultado.productos_esenciales_totales` |
| `numero_supermercados` | `1` para la evaluación actual por sucursal; usar el número real si se implementa compra dividida |
| `promociones_aplicables` | `resultado.beneficio_promociones > 0` |

No enviar al endpoint Python:

```text
score
penalizacion_distancia
costo_tiempo
costo_combustible
tipo_vehiculo
km_por_litro
precio_por_litro
```

`penalizacion_distancia` es una señal interna normalizada entre 0 y 1 para
ordenar alternativas en Laravel. No reemplaza a `distancia_adicional_km` en
R03: esa regla usa umbrales expresados en kilómetros. Por eso el adaptador
debe calcular la distancia mínima del conjunto antes de llamar a Python.

Las alternativas sin coordenadas físicas (`distancia_km = null`), como una
posible tienda en línea, no deben enviarse a Python en la primera versión:
`RecommendationRequest` exige una distancia numérica y las reglas de
conveniencia necesitan distancia y tiempo. Laravel debe conservarlas en su
optimización y marcar la recomendación experta como no disponible para esa
alternativa.

El backend actual evalúa una sucursal por alternativa, así que
`numero_supermercados` vale `1` en esta integración. Los escenarios Python de
dos o tres supermercados siguen siendo pruebas del motor y solo deben usarse
cuando Laravel implemente explícitamente una compra dividida.

## Configuración

En el `.env` de Laravel:

```dotenv
EXPERT_SYSTEM_URL=http://127.0.0.1:8001
EXPERT_SYSTEM_TIMEOUT=3
EXPERT_SYSTEM_RETRY_TIMES=1
```

El ejemplo de configuración está en
`examples/laravel/config/services.php` y debe incorporarse al
`config/services.php` real de Laravel.

## Endpoint de recomendación

### Datos HTTP

```text
Método:  POST
Ruta:    /api/v1/recommend
URL:     {EXPERT_SYSTEM_URL}/api/v1/recommend
Timeout: 3 segundos
```

Headers:

```http
Accept: application/json
Content-Type: application/json
```

Laravel debe enviar los campos públicos del contrato:

```json
{
  "request_id": "demo-001",
  "alternativa_id": "supermercado-1",
  "costo_total": 42.5,
  "presupuesto": 50.0,
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
```

Respuesta HTTP 200:

```json
{
  "request_id": "demo-001",
  "nivel_recomendacion": "EXCELENTE",
  "accion_sugerida": "Comprar todo en esta alternativa.",
  "explicacion": "Cumple el presupuesto, incluye los esenciales y requiere un recorrido conveniente.",
  "reglas_activadas": ["R06", "R07"],
  "prioridad_aplicada": "CONVENIENCIA",
  "hechos_derivados": {
    "dentro_presupuesto": true,
    "ahorro_alto": true,
    "distancia_cercana": true,
    "diferencia_presupuesto": 7.5
  },
  "version_reglas": "1.0.0",
  "winning_rule": "R06",
  "losing_rules": ["R07"],
  "trace": []
}
```

`trace` contiene la trazabilidad completa cuando se solicita directamente al
servicio. Laravel no debe interpretarla para duplicar el motor; puede
mostrarla o registrarla como información explicativa.

## Endpoint de chatbot

```text
Método:  POST
Ruta:    /api/v1/chat
URL:     {EXPERT_SYSTEM_URL}/api/v1/chat
Timeout: 3 segundos
```

Body:

```json
{
  "message": "¿Por qué no se recomienda esta alternativa?",
  "facts": {
    "costo_total": 42.5,
    "presupuesto": 50.0,
    "ahorro": 1.5,
    "distancia_adicional_km": 10.0,
    "tiempo_estimado_min": 35,
    "productos_disponibles": 7,
    "productos_totales": 8,
    "productos_esenciales_disponibles": 5,
    "productos_esenciales_totales": 5,
    "numero_supermercados": 1,
    "promociones_aplicables": false
  },
  "recommendation": {
    "request_id": "demo-002",
    "nivel_recomendacion": "NO_RECOMENDABLE",
    "accion_sugerida": "Elegir una alternativa más cercana.",
    "explicacion": "El ahorro obtenido no compensa la distancia adicional requerida.",
    "reglas_activadas": ["R03"],
    "prioridad_aplicada": "DISTANCIA_AHORRO",
    "hechos_derivados": {
      "dentro_presupuesto": true,
      "ahorro_bajo": true,
      "distancia_lejana": true
    },
    "version_reglas": "1.0.0"
  }
}
```

Respuesta HTTP 200:

```json
{
  "request_id": "demo-002",
  "intent": "EXPLICACION",
  "response": "La recomendación actual es NO_RECOMENDABLE porque el ahorro obtenido no compensa la distancia adicional requerida. Reglas activadas: R03.",
  "supported": true
}
```

## Qué no debe enviar Laravel

Laravel no debe enviar:

- Consultas SQL.
- Conexiones a PostgreSQL.
- Modelos Eloquent completos.
- IDs internos que no formen parte del contrato.
- Datos completos de tablas.
- Reglas.
- Lambdas o lógica de inferencia.
- Decisiones ya inventadas por Laravel.

Debe enviar solo hechos necesarios y validados para la alternativa analizada.

## Códigos HTTP y errores

| Código | Significado | Acción de Laravel |
|---|---|---|
| 200 | Recomendación o respuesta de chatbot válida | Consumir la respuesta |
| 422 | JSON inválido o inconsistente | Registrar advertencia y continuar con fallback |
| 500 | Error interno del servicio Python | Registrar error técnico y continuar |
| Sin respuesta | Timeout, DNS, conexión rechazada o servicio apagado | Registrar advertencia y continuar |

La primera versión no requiere autenticación ni CORS: la comunicación será
servidor a servidor. Si posteriormente el servicio se expone fuera de la red
privada, se debe revisar autenticación, autorización y protección de red.

## Fallback

El fallback debe ser el resultado del motor de optimización que Laravel ya
tenga. No debe crear una recomendación experta alternativa.

Ejemplo conceptual:

```php
$expertRecommendation = $client->recommend($facts);

$viewData['recommendation'] = $expertRecommendation
    ?? $optimizationResult;
$viewData['expert_available'] = $expertRecommendation !== null;
```

Así SmartMarket puede continuar mostrando costos, rutas y optimización aunque
Python esté apagado.

## Cliente Laravel de ejemplo

El archivo [ExpertSystemClient.php](../examples/laravel/app/Services/ExpertSystemClient.php)
usa el HTTP Client nativo de Laravel, timeout de 3 segundos y un único retry
limitado. Los logs solo incluyen endpoint, código HTTP y tipo de error; no
incluyen payloads, precios, productos ni datos personales.

La ubicación es `examples/laravel/` porque este repositorio contiene el
servicio Python. En el proyecto Laravel real se copia a:

```text
app/Services/ExpertSystemClient.php
config/services.php
```

Uso:

```php
$client = app(\App\Services\ExpertSystemClient::class);
$recommendation = $client->recommend($facts);
$chat = $client->chat($chatPayload);
```

El ejemplo conceptual de prueba está en
`examples/laravel/tests/Unit/ExpertSystemClientTest.php`.

## Limitaciones de esta integración

- No modifica el motor Python.
- No agrega dependencia de Python hacia Laravel.
- No agrega base de datos.
- No incorpora autenticación.
- No implementa colas ni historial permanente.
- El retry es deliberadamente corto para no bloquear la solicitud principal.
