# SmartMarket SV — Backend (Laravel)

API de Laravel que alimenta a SmartMarket SV: catálogo maestro de productos, comparador de
precios entre supermercados, listas de compra y el Motor de Optimización que calcula la mejor
alternativa de compra según costo, combustible, tiempo y promociones.

Proyecto de emprendimiento social para las materias de **Emprendedurismo** y **Sistemas Expertos**.

---

## Stack

| Componente | Tecnología |
|---|---|
| Framework | Laravel 13 (PHP 8.3) |
| Base de datos | PostgreSQL (requiere la extensión `unaccent`) |
| Autenticación | Laravel Sanctum (token Bearer) |
| Panel admin | Filament 5.7 |
| Optimización | Servicios propios (`app/Services/Optimization`) |

> **Importante:** el Buscador Universal usa `unaccent()` en SQL crudo, por lo que PostgreSQL es
> obligatorio. No se puede correr con SQLite aun cuando `.env.example` tenga ese valor por defecto.

---

## Requisitos previos

- PHP >= 8.3
- Composer
- PostgreSQL con la extensión `unaccent` habilitada
- `shared/demo_products.json` en la raíz del repo (lo lee `DemoDataSeeder` vía `base_path('../shared/…')`)

---

## Instalación

```bash
composer install
cp .env.example .env

# En .env apuntar a PostgreSQL:
#   DB_CONNECTION=pgsql
#   DB_HOST=127.0.0.1
#   DB_PORT=5432
#   DB_DATABASE=smartmarket
#   DB_USERNAME=...
#   DB_PASSWORD=...

php artisan key:generate
php artisan migrate --seed
php artisan serve          # http://127.0.0.1:8000
```

También existen scripts de Composer:

```bash
composer setup             # instala dependencias, crea .env, key, migra y compila assets
composer dev               # corre servidor + queue + logs + Vite en paralelo (concurrently)
composer test              # ejecuta la suite de tests
```

---

## Estructura

```
backend-laravel/
├── app/
│   ├── Filament/             # panel administrativo (productos, precios, staging, sync, usuarios)
│   ├── Http/Controllers/     # Auth, Producto, Categoria, Sucursal, Promocion, ListaCompra
│   ├── Models/               # Producto, Categoria, AliasProducto, Supermercado, Sucursal,
│   │                         #   PrecioActual, HistorialPrecio, ListaCompra, ListaCompraDetalles,
│   │                         #   ProductoRaw, SyncRun, ResultadoOptimizacion, User
│   ├── Services/
│   │   ├── NormalizadorTexto.php          # limpieza sin tildes / minúsculas (Buscador)
│   │   ├── ExpertSystemService.php        # cliente HTTP hacia el Sistema Experto (recommend/chat)
│   │   ├── Optimization/
│   │   │   ├── ComparisonService.php      # costo total de una lista por sucursal
│   │   │   ├── DistanceService.php        # Haversine
│   │   │   └── OptimizationService.php    # Score, ordenamiento, payloads y persistencia
│   │   └── PriceProviders/                # extractores: Super Selectos (HTML) y tiendas VTEX
├── config/
│   ├── optimization.php                   # pesos α/β/γ/δ y supuestos del MVP (configurables por env)
│   └── services.php                       # URL/timeout/retry del Sistema Experto
├── database/
│   ├── migrations/                        # ERD v1.0 (ver docs/02-arquitectura.md)
│   └── seeders/                           # DatabaseSeeder, DemoDataSeeder, UserSeeder
├── routes/
│   └── api.php                            # todas las rutas JSON
└── tests/                                 # 117 pruebas (Unit + Feature)
```

Arquitectura por capas **Controller → Service → Model** (ADR-005): los controladores solo coordinan
la petición; el cálculo vive en servicios probables de forma aislada.

---

## API

Base: `http://127.0.0.1:8000/api`

### Públicas

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/register` | Crear usuario |
| POST | `/login` | Iniciar sesión → devuelve token Sanctum |
| GET | `/productos` | Catálogo maestro (paginado, filtro `categoria_id`) |
| GET | `/productos/{producto}` | Detalle con precios actuales por sucursal |
| GET | `/productos/{producto}/historial?dias=90` | Historial de precios por sucursal (array plano) |
| GET | `/productos/buscar?q=…` | Buscador Universal (nombre/marca/alias + relevancia) |
| GET | `/categorias` | Categorías del catálogo |
| GET | `/sucursales` | Sucursales de los supermercados (excluye la tienda en línea) |
| GET | `/promociones` | Precios con promoción activa (filtro `categoria_id`) |

### Protegidas (header `Authorization: Bearer {token}`)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/logout` | Revocar token |
| GET | `/me` | Usuario autenticado |
| GET | `/listas` | Listas del usuario |
| POST | `/listas` | Crear lista (con `productos[]` opcionales) |
| GET | `/listas/{lista}` | Detalle de la lista |
| DELETE | `/listas/{lista}` | Eliminar lista |
| PATCH | `/listas/{lista}/completar` | Marcar la compra como realizada |
| PATCH | `/listas/{lista}/reactivar` | Volver a marcarla como activa |
| GET | `/listas/{lista}/comparar` | Comparación de precios por sucursal |
| GET | `/listas/{lista}/promociones` | Promociones de los productos de esta lista |
| GET | `/listas/{lista}/optimizar?lat=…&lng=…` | Mejor alternativa con Score + recomendación experta |
| POST | `/listas/{lista}/chat` | Chat explicativo sobre una alternativa optimizada |
| POST | `/listas/{lista}/productos` | Agregar producto |
| PATCH | `/listas/{lista}/productos/{detalle}` | Actualizar cantidad/esencial |
| DELETE | `/listas/{lista}/productos/{detalle}` | Quitar producto |

---

## Buscador Universal

`GET /productos/buscar?q=…` compara el término contra **nombre**, **marca** y **alias** usando el
mismo criterio de normalización del Motor de Normalización del MVP:

1. **Multi-palabras:** cada palabra del término debe aparecer en nombre/marca (o todas dentro de un
   mismo alias), sin importar el orden.
2. **Relevancia:** coincidencia exacta → empieza con → contiene, vía `CASE` en `ORDER BY`.

Usa `unaccent(lower(...))`, de ahí el requisito de PostgreSQL.

---

## Motor de Optimización

Formula del Score (congelada en `02-arquitectura.md` sección 5.1, ADR-008):

```
Score = α · CostoCompra + β · PenalizacionDistancia + γ · CostoTiempo − δ · BeneficioPromociones
```

- **Menor Score = mejor alternativa** (es costo ajustado, no una calificación).
- Los pesos `α/β/γ/δ` no están hardcodeados: se configuran con `OPTIMIZATION_ALPHA/BETA/GAMMA/DELTA`
  y otros supuestos del MVP (`VELOCIDAD_PROMEDIO_KMH`, `COSTO_POR_MINUTO`) en `config/optimization.php`.
  (`FUEL_PRICE` / `VEHICLE_KM_PER_LITRE` están reservados para v2, ver ADR-05: en el MVP la distancia
  se normaliza y no se dolariza el combustible).
- Distancia por **Haversine** (`DistanceService`), tiempo estimado con velocidad urbana promedio
  constante (supuesto del MVP, sin tráfico real).
- El flujo completo lo orquesta `OptimizationService::optimizar()` y persiste el resultado en
  `ResultadoOptimizacion` (`resultado_json` guarda el detalle).

---

## Sistema Experto

Laravel es el único que habla con el servicio Python/FastAPI (ADR-009). El servicio vive en un
repositorio aparte y se consume por HTTP:

```dotenv
EXPERT_SYSTEM_URL=https://sistema-experto-fork.onrender.com
EXPERT_SYSTEM_TIMEOUT=15
EXPERT_SYSTEM_RETRY_TIMES=3
EXPERT_SYSTEM_RETRY_SLEEP_MS=2000
EXPERT_SYSTEM_API_KEY=
```

- `EXPERT_SYSTEM_API_KEY` es opcional: si está vacío, no se envía el header `X-API-Key`.
- `GET /api/listas/{lista}/optimizar` envía un payload por alternativa y adjunta
  `recommendation` + `expert_system_available` a cada resultado.
- `POST /api/listas/{lista}/chat` reconstruye los hechos desde `resultado_json` y llama a
  `/api/v1/chat`.
- Si el experto falla, la optimización sigue funcionando y el chat responde con
  `supported=false` / `intent=NO_DISPONIBLE`.
- **Ojo con la latencia:** Render free duerme el servicio tras un periodo de inactividad. Con el
  timeout y reintentos actuales, la primera optimización del día puede tardar bastante.

El detalle del contrato, reglas y fallback está en `docs/CONTEXTO-SISTEMA-EXPERTO.md`.

### Rate limiting

Los límites se definen en `AppServiceProvider` y se aplican desde `bootstrap/app.php` y
`routes/api.php`:

| Limitador | Límite | Se aplica a |
|---|---|---|
| `api` | 60 req/min por usuario o IP | Toda la API |
| `auth` | 5 req/min por email + IP | `POST /login`, `POST /register` |
| `expert` | 20 req/min por usuario o IP | `GET /listas/{lista}/optimizar`, `POST /listas/{lista}/chat` |

---

## Pipeline de precios

El extractor automático (v1.1) está implementado con staging y validación:

```
Price Provider (Super Selectos HTML / VTEX)
  → producto_raw (staging)
  → Normalización y validación
  → Catálogo Maestro + PrecioActual (+ HistorialPrecio)
```

- `php artisan precios:sync` recolecta hacia staging y registra la corrida en `sync_runs`.
- `php artisan precios:procesar` publica las filas válidas y archiva el precio anterior.
- Ambos comandos aceptan `--dry-run` y respetan el apagado por configuración.
- PriceSmart permanece con carga manual (ADR-10).
- Todo es administrable desde el panel Filament (staging, corridas y precios).

---

## Datos demo

`php artisan db:seed` carga desde `shared/demo_products.json`:

- Categorías, supermercados y sucursales (con coordenadas).
- Productos, aliases y precios actuales (con promociones).

El seeder es **idempotente** (`firstOrCreate` / `updateOrCreate`). El SKU lógico del JSON (ej.
`FOREMOST-LECHE-1L`) se usa solo como clave interna del seeder; todavía no es columna en `productos`
(ver nota al final de `DemoDataSeeder.php`).

---

## Calidad

```bash
composer test          # 117 pruebas (limpia el cache de config y usa SQLite en memoria)
./vendor/bin/pint      # formateo de código
```

> Si corrés `php artisan test` directamente y el proyecto tiene `bootstrap/cache/config.php`,
> Laravel usará la configuración cacheada (PostgreSQL) e ignorará el SQLite de `phpunit.xml`.
> En ese caso ejecutá `php artisan config:clear` o usá `composer test`.

---

## Documentación

- `docs/00-contexto-proyecto.md` — resumen ejecutivo para retomar desarrollo
- `docs/02-arquitectura.md` — arquitectura congelada (ERD v1.0, ADRs 001-011, Motor de Normalización)
- `docs/03-plan-implementacion.md` — roadmap, fases y Definition of Done
- `docs/04-sistema-experto.md` — Sistema Experto (Python) que consume esta API
- `docs/05-decision-costo-combustible.md` — ADR-05 (`PenalizacionDistancia`)
- `docs/06-referencia-extractor-vtex.md` y `07-decision-extractor-fuentes-riesgo.md` — pipeline de precios y ADR-10
- `docs/08-decision-sucursal-tienda-online.md` — ADR-11 (sucursal sin coordenadas)
- `docs/09-preguntas-chat-experto.md` — temas que responde el chat
- `docs/CONTEXTO-SISTEMA-EXPERTO.md` — guía de integración Laravel ↔ Python
