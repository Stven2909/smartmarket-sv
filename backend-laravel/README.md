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
│   ├── Http/Controllers/     # Auth, Producto, Categoria, Sucursal, Promocion, ListaCompra
│   ├── Models/               # Producto, Categoria, AliasProducto, Supermercado, Sucursal,
│   │                         #   PrecioActual, HistorialPrecio, ListaCompra, ListaCompraDetalles,
│   │                         #   ResultadoOptimizacion, User
│   ├── Services/
│   │   ├── NormalizadorTexto.php          # limpieza sin tildes / minúsculas (Buscador)
│   │   └── Optimization/
│   │       ├── ComparisonService.php      # costo total de una lista por sucursal
│   │       ├── DistanceService.php        # Haversine + costo de combustible
│   │       └── OptimizationService.php    # Score, ordenamiento y persistencia
├── config/
│   ├── optimization.php                   # pesos α/β/γ/δ y supuestos del MVP (configurables por env)
├── database/
│   ├── migrations/                        # ERD v1.0 (ver docs/02-arquitectura.md)
│   └── seeders/                           # DatabaseSeeder, DemoDataSeeder, UserSeeder
├── routes/
│   └── api.php                            # todas las rutas JSON
└── tests/
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
| GET | `/productos/buscar?q=…` | Buscador Universal (nombre/marca/alias + relevancia) |
| GET | `/categorias` | Categorías del catálogo |
| GET | `/sucursales` | Sucursales de los supermercados |
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
| GET | `/listas/{lista}/comparar` | Comparación de precios por sucursal |
| GET | `/listas/{lista}/optimizar?lat=…&lng=…` | Mejor alternativa con Score |
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
Score = α · CostoCompra + β · CostoCombustible + γ · CostoTiempo − δ · BeneficioPromociones
```

- **Menor Score = mejor alternativa** (es costo ajustado, no una calificación).
- Los pesos `α/β/γ/δ` no están hardcodeados: se configuran con `OPTIMIZATION_ALPHA/BETA/GAMMA/DELTA`
  y otros supuestos del MVP (`FUEL_PRICE`, `VEHICLE_KM_PER_LITRE`, `VELOCIDAD_PROMEDIO_KMH`,
  `COSTO_POR_MINUTO`) en `config/optimization.php`.
- Distancia por **Haversine** (`DistanceService`), tiempo estimado con velocidad urbana promedio
  constante (supuesto del MVP, sin tráfico real).
- El flujo completo lo orquesta `OptimizationService::optimizar()` y persiste el resultado en
  `ResultadoOptimizacion` (`resultado_json` guarda el detalle).

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
composer test          # suite PHPUnit (usa SQLite en memoria)
./vendor/bin/pint      # formateo de código
```

---

## Documentación

- `docs/00-contexto-proyecto.md` — resumen ejecutivo para retomar desarrollo
- `docs/02-arquitectura.md` — arquitectura congelada (ERD v1.0, ADRs 001-009, Motor de Normalización)
- `docs/03-plan-implementacion.md` — roadmap, fases y Definition of Done
- `docs/04-sistema-experto.md` — Sistema Experto (Python) que consumirá esta API
