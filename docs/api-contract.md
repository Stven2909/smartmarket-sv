# Contrato público de la API Python

Versión del contrato: `1.0.0`  
Versión de reglas: `1.0.0`

El contrato generado por FastAPI está en [openapi.json](openapi.json). Laravel
es el orquestador; Python valida hechos, deriva valores internos, evalúa
reglas, resuelve conflictos y devuelve una explicación determinista.

## Endpoints

| Método | Ruta | Uso |
|---|---|---|
| `GET` | `/health` | Verificar disponibilidad |
| `POST` | `/api/v1/recommend` | Obtener recomendación e índice auxiliar |
| `POST` | `/api/v1/chat` | Explicar una recomendación |

Para los endpoints JSON:

```http
Accept: application/json
Content-Type: application/json
```

## POST /api/v1/recommend

Todos los campos son obligatorios. Las unidades y restricciones son:

| Campo | Tipo | Unidad o rango |
|---|---|---|
| `request_id` | string | No vacío |
| `alternativa_id` | string | No vacío |
| `costo_total` | float | `>= 0`, moneda del proyecto |
| `presupuesto` | float | `> 0`, no acepta `null` |
| `ahorro` | float | `>= 0`, moneda del proyecto |
| `distancia_km` | float | `>= 0`, kilómetros |
| `distancia_adicional_km` | float | `>= 0`, kilómetros |
| `tiempo_estimado_min` | float | `>= 0`, minutos |
| `productos_disponibles` | integer | `>= 0`, no mayor que el total |
| `productos_totales` | integer | `> 0` |
| `productos_esenciales_disponibles` | integer | `>= 0`, no mayor que el total esencial |
| `productos_esenciales_totales` | integer | `> 0` |
| `numero_supermercados` | integer | `>= 1`; actualmente `1` |
| `promociones_aplicables` | boolean | `true` o `false` |

Request válido:

```json
{
  "request_id": "demo-001",
  "alternativa_id": "supermercado-1",
  "costo_total": 42.50,
  "presupuesto": 50.00,
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

Laravel debe calcular:

```text
ahorro = max(0, costo_referencia - costo_actual)
distancia_adicional_km = max(0, distancia_actual - distancia_minima)
```

Si `presupuesto`, `distancia_km` o `tiempo_minutos` son `null`, o una
sucursal no tiene coordenadas, Laravel debe omitir la llamada y continuar con
su optimización:

```json
{
  "recommendation": null,
  "expert_system_available": false
}
```

Python conserva el contrato estricto y devuelve `422` si recibe esos valores
nulos o datos inconsistentes.

### Campos que no debe enviar Laravel

No forman parte del contrato Python:

```text
score
penalizacion_distancia
costo_tiempo
costo_combustible
tipo_vehiculo
km_por_litro
precio_por_litro
latitud
longitud
```

Tampoco deben enviarse SQL, modelos Eloquent completos, reglas, datos de
tablas completas ni lógica de inferencia.

### Response 200

La respuesta combina la decisión del motor con información auxiliar:

```json
{
  "request_id": "demo-001",
  "nivel_recomendacion": "EXCELENTE",
  "accion_sugerida": "Comprar todo en esta alternativa.",
  "explicacion": "Cumple el presupuesto y las condiciones principales.",
  "reglas_activadas": ["R06", "R07"],
  "prioridad_aplicada": "CONVENIENCIA",
  "hechos_derivados": {
    "dentro_presupuesto": true,
    "todos_esenciales_disponibles": true,
    "porcentaje_productos_disponibles": 100.0
  },
  "version_reglas": "1.0.0",
  "version_contrato": "1.0.0",
  "winning_rule": "R06",
  "losing_rules": ["R07"],
  "trace": [],
  "indice_conveniencia": 82.39,
  "clasificacion_conveniencia": "ALTA_CONVENIENCIA",
  "componentes_conveniencia": {
    "ahorro": 0.5625,
    "disponibilidad": 1.0,
    "distancia": 0.96,
    "tiempo": 0.9,
    "promociones": 1.0
  },
  "pesos_conveniencia": {
    "ahorro": 0.35,
    "disponibilidad": 0.25,
    "distancia": 0.2,
    "tiempo": 0.15,
    "promociones": 0.05
  }
}
```

Los campos `winning_rule`, `losing_rules` y `trace` permiten auditoría. El
índice nunca cambia `nivel_recomendacion`, `accion_sugerida`,
`winning_rule`, `losing_rules` ni `trace`. Las reglas críticas R01–R05 tienen
precedencia.

Niveles públicos:

- `EXCELENTE`.
- `BUENA`.
- `NO_RECOMENDABLE`.

Clasificaciones auxiliares:

- `ALTA_CONVENIENCIA`: índice `>= 75`.
- `CONVENIENCIA_MEDIA`: índice `>= 50` y `< 75`.
- `BAJA_CONVENIENCIA`: índice `< 50`.

`score` pertenece al optimizador Laravel y no es usado por Python.

### Códigos de respuesta

| Código | Significado | Acción de Laravel |
|---|---|---|
| `200` | Recomendación válida | Consumir la respuesta |
| `422` | Contrato inválido o inconsistente | Registrar y usar fallback |
| `500` | Error interno no controlado | Registrar y usar fallback |
| Timeout/conexión | Python no disponible | Continuar sin recomendación experta |

Ejemplo `422`:

```json
{
  "detail": [
    {
      "loc": ["body", "presupuesto"],
      "msg": "Input should be greater than 0",
      "type": "greater_than"
    }
  ]
}
```

## POST /api/v1/chat

Laravel envía el mensaje, los hechos disponibles y la recomendación recibida
en la solicitud actual. El chatbot no recalcula reglas ni inventa datos.

```json
{
  "message": "¿Por qué se recomienda esta alternativa?",
  "facts": {
    "costo_total": 42.5,
    "presupuesto": 50.0,
    "ahorro": 11.25,
    "distancia_adicional_km": 0.8,
    "tiempo_estimado_min": 12
  },
  "recommendation": {
    "request_id": "demo-001",
    "nivel_recomendacion": "EXCELENTE",
    "accion_sugerida": "Comprar todo en esta alternativa.",
    "explicacion": "Cumple el presupuesto y las condiciones principales.",
    "reglas_activadas": ["R06", "R07"],
    "prioridad_aplicada": "CONVENIENCIA",
    "hechos_derivados": {"dentro_presupuesto": true},
    "version_reglas": "1.0.0",
    "version_contrato": "1.0.0"
  }
}
```

Response:

```json
{
  "request_id": "demo-001",
  "intent": "EXPLICACION",
  "response": "La recomendación actual es EXCELENTE porque cumple el presupuesto y las condiciones principales.",
  "supported": true
}
```

## Compatibilidad y fallback

El contrato puede consumirse mediante Swagger en `/docs`, PowerShell,
`requests` de Python o el HTTP Client de Laravel. Laravel debe configurar un
timeout aproximado de tres segundos, un retry limitado y una respuesta de
respaldo. Si Python no responde, Laravel conserva costo, ahorro, score,
distancia, tiempo, disponibilidad y sucursal; solo deja `recommendation` en
`null` y `expert_system_available` en `false`.
