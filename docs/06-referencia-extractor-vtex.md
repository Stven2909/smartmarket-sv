# Referencia técnica: Extractor automático de precios (v1.1)

> **Estado: REFERENCIA — esto no implementa nada hoy.**
>
> Este documento conserva el análisis técnico del extractor automático de precios
> que ya resolvió un proyecto hermano (repo privado `IsaacRenderos2109/smartmarket-sv`,
> clonado y analizado el 2026-08-22). El roadmap (`03-plan-implementacion.md`, sección 7)
> mantiene el extractor como mejora v1.1 que **no bloquea la entrega** — igual que este
> análisis: documentado ahora mientras está fresco, sin comprometer implementación.
>
> - ✅ **Se adopta:** los *patrones* (estrategia VTEX, cortesía HTTP, pipeline de datos).
> - ❌ **No se adopta:** el código Python/Node literal ni su stack externo
>   (Cloudflare Workers/D1/MongoDB/Redis) — el nuestro es Laravel + PostgreSQL (ADR-001).
> - ⚠️ **Pendiente antes de ejecutar cualquier cosa:** revisión legal de los términos de
>   uso (ToS) de cada supermercado, ver `02-arquitectura.md` sección 6.5. Si una fuente
>   no se puede automatizar, el sistema sigue funcionando con carga manual.

---

## 1. Decisión

| Aspecto | Decisión | Por qué |
|---|---|---|
| Estrategia VTEX (API pública del e-commerce) | ✅ Adoptar como patrón | Es la parte más aprovechable: JSON estructurado, sin parsing frágil de HTML |
| Patrones de cortesía HTTP | ✅ Adoptar | UA identificable, reintentos con backoff, abortar ante bloqueo — nunca evadir controles |
| Código literal del repo hermano (Python ETL / conectores Node) | ❌ Descartar | Stack incompatible con el nuestro; solo sirve como especificación de comportamiento |
| Su infraestructura (Workers, D1, MongoDB, Redis) | ❌ Descartar | Duplicaría lógica fuera de nuestra arquitectura congelada (ADR-001/ADR-006) |
| Fuente "partner feed" (convenio firmado) | 🔒 Idea reservada | Coincide con nuestra fuente "API oficial" de v1.2; requiere acuerdo comercial |

---

## 2. Hallazgos del análisis

### 2.1 Fuentes y modos soportados

El repo hermano trata cada supermercado como una *fuente* con un modo de extracción,
registradas en una tabla gobernada (nada hardcodeado en la lógica):

| Supermercado | Modo | URL base | Estado | Productos estimados |
|---|---|---|---|---|
| Super Selectos | `html` | `https://www.superselectos.com/` | activo | ~12,000 |
| Maxi Despensa | `vtex` | `https://www.maxidespensa.com.sv` | activo | ~11,000 |
| La Despensa de Don Juan | `vtex` | `https://www.ladespensadedonjuan.com.sv` | activo | ~14,000 |
| Walmart El Salvador | `vtex` | `https://www.walmart.com.sv` | activo | ~25,000 |
| Súper San Francisco | `partner-feed` | (requiere convenio + token) | deshabilitado | ~1,800 |

Fuentes retiradas por romperse o no ser viables: Pricesmart, EPA, Super 7, etc.
Lección: las fuentes son desechables por diseño — el resto del sistema nunca depende
de ninguna en particular (mismo principio que nuestra §6.1).

### 2.2 Estrategia VTEX (lo más aprovechable)

Maxi Despensa, Don Juan y Walmart SV corren sobre **VTEX**, una plataforma de
e-commerce cuya API pública de catálogo devuelve JSON limpio. Sin tocar HTML:

```
1. GET {base}/api/catalog_system/pub/category/tree/10
   → árbol de categorías; se recorren solo las hojas.

2. GET {base}/api/catalog_system/pub/products/search
        ?fq=C:{categoria_id}&_from={n}&_to={n+49}
   → paginación de a 50 productos por categoría.
   El total real viene en el header `resources` (regex `/(\d+)$`).

3. De cada producto:
   - ofertas = items × sellers donde commertialOffer.Price > 0
   - se toma la oferta de MENOR precio (min por Price)
   - precio anterior = ListPrice (solo si ListPrice > Price)
   - disponibilidad = AvailableQuantity > 0 ? disponible : publicado
   - unidad = unitMultiplier + measurementUnit
   - imagen = primera imageUrl del item

4. Deduplicación por {fuente}:{sku} dentro de la corrida.
```

Ventajas sobre scrapear HTML: estable ante rediseños de la página web, datos ya
estructurados (SKU, categoría, imágenes, stock), y es exactamente el mecanismo que
el propio sitio usa para renderizarse.

### 2.3 Modo HTML (Super Selectos)

Fallback clásico con BeautifulSoup para el sitio que no usa VTEX:

- Tarjetas de producto: selectores `.producto-box`, `.product-item`, `article`.
- Nombre: `.prod-nombre` / `h5` / `h3`.
- Precios: regex `\$\s*(\d+(?:\.\d{1,2})?)` sobre `.precios .precio`, `.price-current`, `.price-old`.
- Heurística de promo: `precio_actual = min(precios_encontrados)`,
  `precio_anterior = max(...)` solo si es mayor al actual.
- URL e imagen relativas resueltas contra la base (`urljoin`).

Es el más frágil de los dos modos: cualquier rediseño lo rompe (ver riesgo
"Un supermercado cambia su página web" en `03-plan-implementacion.md`).

### 2.4 Cortesía HTTP y postura de cumplimiento

Patrones transversales a todos los modos:

- **User-Agent identificable**: `SmartMarketSV/1.0 (+authorized catalog synchronization)`
  (configurable por variable de entorno). No se hace pasar por navegador.
- **Reintentos acotados**: hasta 4 intentos ante HTTP 429/503 con backoff exponencial
  (`0.5s × 2^intento`); agotados → error `source_retry_budget_exhausted`.
- **Rate-limit propio**: pausa fija (~120 ms) entre páginas consecutivas de la misma fuente.
- **Detección de bloqueo SIN evasión**: si la respuesta contiene captcha / access denied /
  verify you are human, la corrida marca `source_access_control_detected` y aborta esa
  fuente. Nunca resuelve captchas ni rota identidades.
- Filosofía declarada en su registro de fuentes: *"enabled significa que existe un
  mecanismo público revisado que puede ejecutarse sin autenticación ni evasión de
  controles"* — coherente con nuestra nota legal §6.5.

### 2.5 Normalización del dato crudo

Su equivalente a nuestro Motor de Normalización (§6.2):

- Texto: descomposición Unicode (quita tildes) → minúsculas → solo `[a-z0-9.]`
  (idéntico en espíritu a nuestro `NormalizadorTexto` + extensión `unaccent`).
- Clave canónica del producto: `sha256(nombre_normalizado | unidad_normalizada)` —
  agrupa el mismo producto entre supermercados sin depender del SKU de cada uno.
- Categorías asignadas por reglas regex ordenadas (8 categorías + "Otros").
- Validaciones duras que rechazan el registro (con motivo contable): nombre fuera de
  3–220 caracteres, precio no decimal o fuera de (0, 100000], URL de fuente no-HTTPS,
  precio anterior ≤ precio actual (en modo ahorros).

### 2.6 Persistencia y trazabilidad

- **Historial append-only**: la tabla de historial de precios solo recibe INSERT con
  fecha — nunca se sobrescribe (es literalmente nuestra Regla fija #1 de §6.3).
- **Ofertas actuales idempotentes**: upsert por `(producto, fuente)` para el estado
  "hoy"; equivalente funcional a nuestra tabla `precios_actuales`.
- **Snapshot crudo auditable**: todo lo recolectado se guarda además tal cual vino
  (documento crudo) en un almacén con TTL de 30 días — es su zona de Staging, análoga
  a nuestro `ProductoRaw` del Flujo 2.
- **Corrida por fuente con conteos**: cada corrida reporta aceptados / rechazados /
  motivos de rechazo por fuente — insumo directo para un Health Monitor (§6.4).

### 2.7 Programación (cuándo corre)

- Cron diario a las 05:00 (hora SV) — "antes de la compra matutina".
- Indexación incremental ligera cada 10 minutos.
- Trigger manual protegido por secreto (`Authorization: Bearer CRON_SECRET`) con
  parámetros: páginas por lote, filtro de fuentes, modo solo-índice.
- Estado de sincronización persistido por fuente (`última corrida exitosa`),
  visible desde la app.

---

## 3. Mapeo hacia nuestra arquitectura

| Concepto del repo hermano | Nuestro equivalente | Ref. `02-arquitectura.md` |
|---|---|---|
| Collector por fuente (`html` / `vtex` / `feed`) | Price Provider (una de las 4 fuentes intercambiables) | §6.1 |
| Registro gobernado de fuentes con `enabled` | Tabla/catálogo de proveedores; carga manual siempre disponible | §6.1 / §6.5 |
| Snapshot crudo con TTL (Mongo) | Zona temporal de Staging (`ProductoRaw`) | Flujo 2 / §6.3 |
| Normalización + clave canónica | Motor de Normalización (+ `NormalizadorTexto` existente) | §6.2 |
| Historial de precios append-only | Regla fija #1: nunca sobrescribir precio anterior | §6.3 |
| `raw_payload` / `source_url` / `fetched_at` | `precios_actuales.origen_dato` + `fecha_actualizacion` | ERD v1.0 |
| Rechazos contados + estado por fuente | Health Monitor (ej.: 1,250→31 productos = alerta) | §6.4 |

Conclusión del mapeo: el diseño hermano es una implementación del mismo pipeline
que ya tenemos especificado — por eso el valor está en los patrones, no en portar código.

---

## 4. Enfoque tentativo cuando llegue v1.1 (no comprometido)

Borrador orientativo, a validar contra ToS y contra el estado del catálogo en ese momento:

1. **Comando Artisan por fuente** (p. ej. `php artisan app:sync-fuentes maxi-despensa`)
   actuando como Price Provider: obtiene → valida → escribe **solo a Staging**, jamás
   directo a `precios_actuales` (§6.3).
2. **Convención de origen**: `origen_dato = 'vtex-maxi-despensa'`, `'html-super-selectos'`,
   `'manual'`, etc., para trazabilidad completa.
3. **HTTP con Laravel `Http` facade**: `timeout`, `retry(3, 500, exponential)`,
   User-Agent identificable y detección temprana de bloqueo (mismos patrones de §2.4).
4. **Normalización**: reutilizar `App\Services\NormalizadorTexto`; la asignación de
   alias sigue siendo manual durante el MVP (fuzzy matching queda en v1.1+ según §6.2).
5. **Health check por corrida**: comparar conteo de productos por fuente contra la
   corrida previa; caída brusca ⇒ alertar y no publicar esa fuente (§6.4).
6. **Nueva migración de Staging**: hoy no existe tabla `producto_raw`; se crearía en
   su momento junto con esta fase, con su TTL/limpieza definidos.
7. **Orden sugerido de fuentes**: empezar por una VTEX (menor fragilidad), dejar
   Super Selectos (modo HTML) para el final.
