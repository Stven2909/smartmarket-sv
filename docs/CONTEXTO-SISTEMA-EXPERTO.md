# SmartMarket SV: guía de integración del Sistema Experto

Documento técnico para el compañero que implementará los cambios en Laravel y
React. Esta guía se basa en el código actual de `Backend-Experto`,
`Frontend-Experto` y `Sistema-Experto-Python`.

## 1. Regla principal de arquitectura

```text
React -> Laravel -> FastAPI Python
```

React solo habla con Laravel. Laravel obtiene datos, calcula la optimización y
llama a Python. Python valida hechos, deriva hechos internos, evalúa reglas y
devuelve una recomendación explicable.

```text
React
  | HTTP + Bearer token
  v
Laravel
  |-- usuarios, listas, catálogo y PostgreSQL/SQLite
  |-- costo, promociones, distancia, tiempo y score
  |-- cliente HTTP hacia Python
  v
FastAPI Python
  |-- Pydantic
  |-- reglas JSON
  |-- inferencia determinista
  |-- chatbot por plantillas
```

No cambiar esta separación. Python no consulta Laravel, PostgreSQL ni modelos
Eloquent. React no llama directamente al puerto 8001.

## 2. Qué hace cada servicio

### Laravel

Laravel debe:

1. Obtener la lista y sus detalles.
2. Consultar precios y promociones.
3. Calcular costo total por sucursal.
4. Calcular distancia, combustible, tiempo y `score`.
5. Construir el JSON del contrato Python.
6. Llamar a FastAPI por HTTP.
7. Adjuntar la recomendación a cada alternativa.
8. Mantener la optimización aunque Python no responda.

Laravel no debe copiar R01-R08 ni decidir los niveles expertos.

### Python

Python debe:

1. Validar la solicitud.
2. Generar hechos derivados.
3. Leer `data/rules.json`.
4. Evaluar condiciones con AND.
5. Resolver conflictos por prioridad.
6. Generar explicación y trazabilidad.

Python no calcula precios, score, rutas ni disponibilidad desde la base de
datos.

### React

React debe mostrar la optimización de Laravel y, si existe, la recomendación
experta. Si Python falla, debe seguir mostrando costo, score, distancia,
tiempo y disponibilidad.

## 3. Estado actual revisado

### Python

Ruta: `Sistema-Experto-Python/`, rama `expert-system-python`.

Archivos relevantes:

```text
app/schemas/recommendation.py
app/schemas/chatbot.py
app/expert_system/classifiers.py
app/expert_system/inference_engine.py
app/expert_system/conflict_resolver.py
data/rules.json
app/api/recommendation_routes.py
app/api/chatbot_routes.py
examples/laravel/app/Services/ExpertSystemClient.php
```

El servicio Python tiene 104 pruebas automatizadas pasando.

### Laravel

Ruta: `Backend-Experto/backend-laravel/`, rama `backend-laravel`.

Flujo actual:

```text
ListaCompraController@optimizar
  -> ComparisonService::comparar()
  -> DistanceService
  -> OptimizationService::calcularScore()
  -> ordenar por score menor
  -> guardar ResultadoOptimizacion
  -> GET /api/listas/{lista}/optimizar
```

Actualmente no existe `app/Services/ExpertSystemClient.php` dentro de Laravel;
solo existe el ejemplo en el proyecto Python.

Rutas actuales importantes:

```text
GET /api/listas/{lista}/comparar
GET /api/listas/{lista}/optimizar?lat={lat}&lng={lng}
GET /api/listas/{lista}/promociones
```

Las rutas de listas usan `auth:sanctum`.

### React

Ruta: `Frontend-Experto/frontend-react/`, rama `frontend-react`.

El frontend ya llama a Laravel mediante `VITE_API_URL`. Las dos vistas que
renderizan resultados de optimización son:

```text
src/components/CompararView.tsx
src/components/ListasView.tsx
```

Los tipos y adaptadores están en:

```text
src/types/api.ts
src/types/domain.ts
src/api/lists.ts
```

Ambas vistas deben recibir la recomendación experta; actualizar solo una
dejaría comportamientos distintos en la aplicación.

## 4. Contrato `POST /api/v1/recommend`

Laravel debe llamar:

```text
POST {EXPERT_SYSTEM_URL}/api/v1/recommend
Content-Type: application/json
Accept: application/json
```

Request exacto:

```json
{
  "request_id": "lista-42-sucursal-3",
  "alternativa_id": "sucursal-3",
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

| Campo | Tipo | Fuente o significado |
|---|---|---|
| `request_id` | string | `lista-{lista_id}-sucursal-{sucursal_id}` |
| `alternativa_id` | string | `sucursal-{sucursal_id}` |
| `costo_total` | float | Suma de `precio_final * cantidad` |
| `presupuesto` | float | Presupuesto de la lista, mayor que cero |
| `ahorro` | float | Ahorro positivo de esta alternativa |
| `distancia_km` | float | Haversine usuario-sucursal |
| `distancia_adicional_km` | float | Distancia extra frente a la más cercana |
| `tiempo_estimado_min` | float | Tiempo calculado por Laravel |
| `productos_disponibles` | int | Detalles con precio en la sucursal |
| `productos_totales` | int | Total de detalles de la lista |
| `productos_esenciales_disponibles` | int | Esenciales con precio |
| `productos_esenciales_totales` | int | Detalles con `esencial=true` |
| `numero_supermercados` | int | Supermercados distintos, no sucursales |
| `promociones_aplicables` | bool | `beneficio_promociones > 0` |

Pydantic rechaza con HTTP 422 números negativos, presupuesto no positivo,
totales no positivos, relaciones de conteo inconsistentes, campos faltantes y
campos desconocidos.

### No enviar estos campos

No enviar `score`, SQL, reglas, modelos Eloquent, tablas, credenciales ni el
registro completo de la base de datos. El esquema Python usa
`extra="forbid"`; enviar `score` provocaría HTTP 422.

### Presupuesto null

Laravel permite `listas_compra.presupuesto = null`, pero Python exige
`presupuesto > 0`. Cuando sea null:

```json
{
  "recommendation": null,
  "expert_system_available": false
}
```

No enviar cero, uno ni un presupuesto inventado. La optimización continúa con
los datos de Laravel.

## 5. Respuesta Python

```json
{
  "request_id": "lista-42-sucursal-3",
  "nivel_recomendacion": "EXCELENTE",
  "accion_sugerida": "Comprar todo en esta alternativa.",
  "explicacion": "Cumple el presupuesto, incluye los esenciales y requiere un recorrido conveniente.",
  "reglas_activadas": ["R06", "R07"],
  "prioridad_aplicada": "CONVENIENCIA",
  "hechos_derivados": {
    "dentro_presupuesto": true,
    "todos_esenciales_disponibles": true,
    "ahorro_alto": true,
    "distancia_cercana": true,
    "tiempo_bajo": true,
    "una_parada": true,
    "diferencia_presupuesto": 7.5,
    "porcentaje_exceso_presupuesto": 0.0,
    "porcentaje_productos_disponibles": 100.0,
    "porcentaje_esenciales_disponibles": 100.0
  },
  "version_reglas": "1.0.0",
  "winning_rule": "R06",
  "losing_rules": ["R07"],
  "trace": []
}
```

`hechos_derivados` tiene `boolean` y `float`; en TypeScript debe ser
`Record<string, boolean | number>`.

Los niveles válidos son exactamente:

```text
EXCELENTE | BUENA | NO_RECOMENDABLE
```

`prioridad_aplicada` es la categoría de la regla ganadora, no el número de
prioridad. `winning_rule`, `losing_rules` y `trace` deben conservarse.

## 6. Reglas y prioridades actuales

La base real está en `Sistema-Experto-Python/data/rules.json`.

| ID | Prioridad | Categoría | Condición | Nivel |
|---|---:|---|---|---|
| R01 | 1 | `PRESUPUESTO` | `presupuesto_muy_excedido` | `NO_RECOMENDABLE` |
| R02 | 2 | `DISPONIBILIDAD` | `faltan_esenciales` | `NO_RECOMENDABLE` |
| R03 | 3 | `DISTANCIA_AHORRO` | `distancia_lejana AND ahorro_bajo` | `NO_RECOMENDABLE` |
| R04 | 3 | `TIEMPO_AHORRO` | `tiempo_alto AND ahorro_bajo` | `NO_RECOMENDABLE` |
| R05 | 4 | `FRAGMENTACION` | `compra_fragmentada` | `NO_RECOMENDABLE` |
| R06 | 5 | `CONVENIENCIA` | presupuesto, esenciales, distancia, tiempo y una parada favorables | `EXCELENTE` |
| R07 | 6 | `PROMOCIONES` | presupuesto, esenciales y promociones favorables | `BUENA` |
| R08 | 5 | `AHORRO_FRAGMENTACION` | `dos_paradas AND ahorro_alto AND dentro_presupuesto` | `BUENA` |

Se devuelven todas las reglas activadas. Gana la de menor número de prioridad.
En empate gana el ID menor, por ejemplo R03 antes de R04. Si ninguna se
activa, Python devuelve la conclusión predeterminada `NO_RECOMENDABLE` con
`prioridad_aplicada = "SIN_REGLA"`.

### Umbrales de hechos derivados

| Hecho | Condición |
|---|---|
| `dentro_presupuesto` | costo menor o igual al presupuesto |
| `presupuesto_ligeramente_excedido` | exceso mayor que 0 y hasta 10% |
| `presupuesto_muy_excedido` | exceso mayor que 10% |
| `todos_productos_disponibles` | disponibles igual a totales |
| `faltan_productos` | disponibles menor que totales |
| `todos_esenciales_disponibles` | esenciales disponibles igual a totales |
| `faltan_esenciales` | esenciales disponibles menor que totales |
| `ahorro_bajo` | ahorro menor que 3.00 |
| `ahorro_medio` | 3.00 <= ahorro < 10.00 |
| `ahorro_alto` | ahorro >= 10.00 |
| `distancia_cercana` | adicional <= 2 km |
| `distancia_media` | adicional > 2 km y < 8 km |
| `distancia_lejana` | adicional >= 8 km |
| `tiempo_bajo` | <= 20 minutos |
| `tiempo_medio` | > 20 y < 45 minutos |
| `tiempo_alto` | >= 45 minutos |
| `una_parada` | exactamente 1 supermercado |
| `dos_paradas` | exactamente 2 supermercados |
| `compra_fragmentada` | 3 o más supermercados |
| `promociones_relevantes` | promociones aplicables verdaderas |

Laravel y React no deben duplicar estas comparaciones.

## 7. Mapeo determinista de Laravel

### Ahorro

Para cada alternativa usar el costo más alto como referencia:

```php
$costoReferencia = max(array_map(
    static fn (array $r): float => (float) $r['costo_total'],
    $resultados,
));

$ahorro = max(
    0.0,
    round($costoReferencia - (float) $resultado['costo_total'], 2),
);
```

No usar el último elemento después de ordenar por score: el peor score no
necesariamente tiene el costo más alto. El campo global `ahorro` que Laravel
guarda puede mantenerse, pero Python recibe el ahorro de cada alternativa.

### Distancia adicional

```php
$distanciaMinima = min(array_map(
    static fn (array $r): float => (float) $r['distancia_km'],
    $resultados,
));

$distanciaAdicional = max(
    0.0,
    round((float) $resultado['distancia_km'] - $distanciaMinima, 2),
);
```

La sucursal más cercana tiene distancia adicional cero. No usar `abs()`.

### Disponibilidad y supermercados

En `ComparisonService` agregar al resultado por sucursal:

```text
supermercado_id
productos_disponibles
productos_totales
```

Se cuentan líneas de detalle, no unidades. Un detalle está disponible si existe
un `PrecioActual` para ese producto y esa sucursal. `numero_supermercados` debe
contar `supermercado_id` distintos, no `sucursal_id`.

## 8. Cambios requeridos en Laravel

### Archivos

```text
app/Services/ExpertSystemClient.php
config/services.php
.env.example
app/Services/Optimization/ComparisonService.php
app/Services/Optimization/OptimizationService.php
tests/Unit/ExpertSystemClientTest.php
tests/Unit/Optimization/OptimizationServiceTest.php
tests/Feature/ListaCompraOptimizationTest.php
```

### Cliente HTTP

Copiar/adaptar `Sistema-Experto-Python/examples/laravel/app/Services/ExpertSystemClient.php`.

Debe ofrecer:

```php
public function recommend(array $facts): ?array;
public function chat(array $payload): ?array;
```

Usar configuración, timeout aproximado de 3 segundos y un retry limitado:

```php
Http::acceptJson()
    ->asJson()
    ->timeout((int) config('services.expert_system.timeout', 3))
    ->retry((int) config('services.expert_system.retry_times', 1), 100, throw: false)
    ->post($url, $payload);
```

Ante HTTP 422, HTTP 500, timeout o conexión, devolver `null`, registrar
endpoint/status/tipo de error y no registrar el payload completo.

### Configuración

En `config/services.php`:

```php
'expert_system' => [
    'url' => env('EXPERT_SYSTEM_URL', 'http://127.0.0.1:8001'),
    'timeout' => (int) env('EXPERT_SYSTEM_TIMEOUT', 3),
    'retry_times' => (int) env('EXPERT_SYSTEM_RETRY_TIMES', 1),
],
```

En `.env.example`:

```dotenv
EXPERT_SYSTEM_URL=http://127.0.0.1:8001
EXPERT_SYSTEM_TIMEOUT=3
EXPERT_SYSTEM_RETRY_TIMES=1
```

En producción solo cambiar `EXPERT_SYSTEM_URL` por la URL pública o privada de
FastAPI. No escribirla en React ni hardcodearla en PHP.

### OptimizationService

Inyectar `ExpertSystemClient`. El orden debe ser:

```text
comparar
  -> calcular distancia, tiempo, combustible y score
  -> calcular costoReferencia y distanciaMinima
  -> construir request por alternativa
  -> llamar Python si presupuesto != null
  -> adjuntar recommendation o null
  -> ordenar por score menor
  -> guardar resultado_json enriquecido
  -> devolver respuesta actual + campos expertos
```

Cada alternativa debe conservar todos sus campos actuales y añadir:

```json
{
  "recommendation": { "request_id": "lista-42-sucursal-3" },
  "expert_system_available": true
}
```

La recomendación real debe contener todos los campos de la respuesta Python.
Si falla:

```json
{
  "recommendation": null,
  "expert_system_available": false
}
```

La ruta actual `GET /api/listas/{lista}/optimizar` puede mantenerse; no es
necesario crear una ruta Laravel adicional para recommendation.

Para el MVP se puede guardar el resultado enriquecido en la columna existente
`resultados_optimizacion.resultado_json`. No crear todavía una tabla nueva.

### Respuesta Laravel esperada

```json
{
  "lista": "Compra semanal",
  "presupuesto": 50.0,
  "mejor_opcion": {
    "sucursal_id": 3,
    "sucursal": "Santa Tecla",
    "supermercado": "Super Selectos",
    "costo_total": 42.5,
    "distancia_km": 2.3,
    "tiempo_minutos": 12.0,
    "score": 44.8,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "recommendation": {
      "request_id": "lista-42-sucursal-3",
      "nivel_recomendacion": "EXCELENTE",
      "accion_sugerida": "Comprar todo en esta alternativa.",
      "explicacion": "Cumple el presupuesto, incluye los esenciales y requiere un recorrido conveniente.",
      "reglas_activadas": ["R06"],
      "prioridad_aplicada": "CONVENIENCIA",
      "hechos_derivados": {},
      "version_reglas": "1.0.0",
      "winning_rule": "R06",
      "losing_rules": [],
      "trace": []
    },
    "expert_system_available": true
  },
  "resultados": [],
  "resultado_optimizacion_id": 15
}
```

Si Python falla, el score y los demás datos deben permanecer y solo cambiar
`recommendation` a `null` y `expert_system_available` a `false`.

## 9. Chatbot

Python expone `POST {EXPERT_SYSTEM_URL}/api/v1/chat` y espera un objeto con
`message`, `facts` originales y `recommendation` completa. El response contiene:

```json
{
  "request_id": "lista-42-sucursal-3",
  "intent": "EXPLICACION",
  "response": "La recomendación actual es EXCELENTE porque cumple el presupuesto, incluye los esenciales y requiere un recorrido conveniente.",
  "supported": true
}
```

Si se habilita en React, crear primero un proxy protegido de Laravel, por
ejemplo `POST /api/expert/chat`. React llama a Laravel y Laravel usa
`ExpertSystemClient::chat()`. Python no debe ser llamado desde el navegador.

Si Python falla, devolver `supported=false` con un mensaje controlado. Esta
parte no debe bloquear la integración de `/optimizar`.

## 10. Cambios requeridos en React

### Tipos

En `src/types/api.ts` agregar:

```ts
export type ApiExpertRecommendation = {
  request_id: string
  nivel_recomendacion: 'EXCELENTE' | 'BUENA' | 'NO_RECOMENDABLE'
  accion_sugerida: string
  explicacion: string
  reglas_activadas: string[]
  prioridad_aplicada: string
  hechos_derivados: Record<string, boolean | number>
  version_reglas: string
  winning_rule: string | null
  losing_rules: string[]
  trace: Array<Record<string, unknown>>
}
```

Extender `ApiOptimizarResultado` con:

```ts
recommendation: ApiExpertRecommendation | null
expert_system_available: boolean
```

En `src/types/domain.ts`, mapear a camelCase como `requestId`, `level`,
`action`, `explanation`, `activatedRules` y `derivedFacts`. El adaptador no
debe eliminar información.

### API y vistas

`src/api/lists.ts` ya usa el endpoint Laravel correcto. Solo debe conservar los
nuevos campos al adaptar la respuesta.

Actualizar ambas vistas:

```text
src/components/CompararView.tsx
src/components/ListasView.tsx
```

Mostrar por alternativa costo, score, distancia, tiempo, disponibilidad, nivel,
acción, explicación, regla ganadora, reglas activadas, prioridad, versión y
`request_id` en el detalle.

Colores:

```text
EXCELENTE       verde
BUENA           amarillo
NO_RECOMENDABLE rojo
```

Cuando `expert_system_available=false`, mostrar un aviso no bloqueante y no
ocultar el resultado de optimización. Se puede extraer la presentación repetida
a `src/components/ExpertRecommendationCard.tsx`; ese componente solo presenta
datos y no contiene reglas.

React usa `VITE_API_URL` para Laravel. En producción:

```dotenv
VITE_API_URL=https://URL-PUBLICA-DE-LARAVEL/api
```

React no debe conocer `EXPERT_SYSTEM_URL`.

## 11. Errores y fallback

| Caso | Laravel | React |
|---|---|---|
| Python 200 | Adjunta recomendación | La muestra |
| Python 422/500 | Log y `recommendation=null` | Mantiene optimización |
| Timeout/DNS | Log y `recommendation=null` | Muestra aviso no bloqueante |
| Presupuesto null | Omite llamada | Explica que falta presupuesto |
| Lista sin productos | Mantiene 422 actual | Muestra error de lista |
| Laravel apagado | No aplica | Muestra error de conexión |

No generar una recomendación falsa desde PHP. No registrar payloads completos,
tokens ni datos personales.

## 12. Pruebas de Laravel

Crear o ampliar:

```text
tests/Unit/ExpertSystemClientTest.php
tests/Unit/Optimization/OptimizationServiceTest.php
tests/Feature/ListaCompraOptimizationTest.php
```

Usar `Http::fake()` para probar HTTP 200, 422, 500, timeout, conexión,
presupuesto null, mapeo de tiempo/promociones, ausencia de `score`, ahorro no
negativo y fallback. También comprobar que el endpoint de optimización sigue
devolviendo HTTP 200 cuando Python está apagado.

Ejecutar desde `Backend-Experto/backend-laravel`:

```powershell
php artisan test
```

## 13. Pruebas de React

Actualmente no hay suite dedicada de componentes. Como mínimo ejecutar desde
`Frontend-Experto/frontend-react`:

```powershell
npm install
npm run build
npm run lint
```

Validación manual:

1. Crear lista con presupuesto.
2. Agregar productos esenciales y opcionales.
3. Ejecutar optimización con latitud y longitud válidas.
4. Verificar score, costo, distancia, tiempo y disponibilidad.
5. Verificar resultados EXCELENTE, BUENA y NO_RECOMENDABLE.
6. Verificar regla ganadora y explicación.
7. Apagar Python y repetir.
8. Confirmar que Laravel mantiene visibles las alternativas.
9. Confirmar que el navegador no llama al puerto 8001.

## 14. Desarrollo local

Python, desde `Sistema-Experto-Python`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Laravel, desde `Backend-Experto/backend-laravel`:

```powershell
php artisan serve --host=127.0.0.1 --port=8000
```

`.env` local:

```dotenv
EXPERT_SYSTEM_URL=http://127.0.0.1:8001
EXPERT_SYSTEM_TIMEOUT=3
EXPERT_SYSTEM_RETRY_TIMES=1
```

React, desde `Frontend-Experto/frontend-react`:

```powershell
npm install
$env:VITE_API_URL="http://127.0.0.1:8000/api"
npm run dev
```

Puertos:

```text
React 5173 -> Laravel 8000 -> Python 8001
```

## 15. Decisiones que no deben modificarse

- No conectar Python directamente a PostgreSQL.
- No hacer que Python consulte Laravel.
- No enviar SQL, modelos Eloquent ni reglas a Python.
- No duplicar R01-R08 en PHP o TypeScript.
- No enviar `score` al contrato Python.
- No inventar presupuesto cuando sea null.
- No derribar la optimización si Python no responde.
- No llamar Python directamente desde React.
- No agregar TensorFlow, PyTorch, scikit-learn ni IA generativa.
- No agregar base de datos al servicio Python.
- No cambiar el contrato sin modificar esquema, pruebas y este documento.

## 16. Criterios de aceptación

La integración queda lista cuando:

- Laravel envía los 14 campos exactos a `/api/v1/recommend`.
- URL, timeout y retry son configurables.
- Presupuesto null omite la llamada.
- Cada alternativa conserva los datos de optimización.
- Cada alternativa incluye recomendación o null.
- Python apagado no produce HTTP 500 en la optimización de Laravel.
- React muestra nivel, acción, explicación, reglas y versión.
- React solo llama a Laravel.
- `php artisan test` y `npm run build` pasan.
- Las 104 pruebas Python continúan pasando.

La integración agrega un cliente HTTP y transforma respuestas; no reescribe el
motor de inferencia ni la base de conocimiento.
