# Referencia técnica: Extractor automático de precios (v1.1)

> **Estado: EN IMPLEMENTACIÓN — Fases 0–3 aprobadas el 2026-08-22 (ADR-10).**
>
> Este documento conserva: (a) el análisis técnico del extractor que ya resolvió un
> proyecto hermano (repo privado `IsaacRenderos2109/smartmarket-sv`, clonado y analizado
> el 2026-08-22) y (b) la revisión legal por supermercado con el plan aprobado
> (secciones 5 y 4). El roadmap (`03-plan-implementacion.md`, sección 7) mantiene el
> extractor como mejora v1.1 que no bloquea la entrega.
>
> - ✅ **Se adopta:** los *patrones* (estrategia VTEX, cortesía HTTP, pipeline de datos).
> - ❌ **No se adopta:** el código Python/Node literal ni su stack externo
>   (Cloudflare Workers/D1/MongoDB/Redis) — el nuestro es Laravel + PostgreSQL (ADR-001).
> - ✅ **Revisión legal completada (2026-08-22):** veredicto por fuente en la sección 5.
>   La decisión informada de riesgo quedó documentada en
>   `07-decision-extractor-fuentes-riesgo.md` (**ADR-10**). Si una fuente se apaga,
>   el sistema sigue funcionando con carga manual.

---

## 1. Decisión

| Aspecto | Decisión | Por qué |
|---|---|---|
| Estrategia VTEX (API pública del e-commerce) | ✅ Adoptar como patrón | Es la parte más aprovechable: JSON estructurado, sin parsing frágil de HTML |
| Patrones de cortesía HTTP | ✅ Adoptar | UA identificable, reintentos con backoff, abortar ante bloqueo — nunca evadir controles |
| Automatizar la familia Walmart pese a ToS restrictivo | ✅ Riesgo académico aceptado (ADR-10) | Solo datos fácticos, cortesía estricta, apagado instantáneo por config — decisión informada del equipo, ver §5.2 |
| PriceSmart como fuente automática | ❌ Excluir de la automatización | Su robots.txt prohíbe scrapers por nombre (§5.3); permanece con carga manual |
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

Nota propia (no del repo hermano): las tres fuentes VTEX pertenecen a una sola empresa
(Operadora del Sur, S.A. de C.V. / Walmart Centroamérica) — suman profundidad de surtido,
no diversidad competitiva. El cruce real entre cadenas independientes es Super Selectos
vs. familia Walmart. Veredicto legal por fuente en §5; PriceSmart se mantiene manual.

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

(Nuestros valores propios de cortesía —User-Agent, pausa, reintentos— están definidos
en §4 punto 3 y son más conservadores que estos.)

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

## 4. Enfoque aprobado — plan de implementación (Fases 0–3)

Aprobado por el equipo el 2026-08-22; la aceptación informada de riesgo está formalizada
en **ADR-10** (`07-decision-extractor-fuentes-riesgo.md`). Un commit por fase.

**Política transversal de contenido:** solo campos fácticos (nombre, precio, unidad,
categoría cruda, URL fuente) — cero logotipos corporativos y cero imágenes de producto
de las tiendas; la UI usa iconos genéricos. El `raw_payload` conserva evidencia completa
para auditoría sin promover contenido creativo a las tablas del catálogo.

| Fase | Entregable |
|---|---|
| 0 — Acta legal + ADR | Veredicto por fuente (§5) + ADR-10 |
| 1 — Staging + config | Migraciones `producto_raw` y `sync_runs`; coordenadas nullable en `sucursales` (+ ADR-11); `config/price_providers.php` con interruptor independiente por fuente |
| 2 — Drivers | `VtexProvider` genérico (cubre Walmart, Maxi Despensa y Don Juan parametrizado por base_url) + `SuperSelectosProvider` (HTML); `PoliteHttpClient` compartido; comando `precios:sync {--fuente=} {--dry-run}`; tests con fixtures locales (`Http::fake()` — jamás tocan red) |
| 3 — Normalización | `StagingProcessor` + comando `precios:procesar`: alias exacto → similitud (`similar_text` ≥ 0.85 sobre texto normalizado) → crear producto+alias si es nuevo; upsert idempotente en `precios_actuales`; append siempre a `historial_precios`; Sucursal "Tienda en línea" excluida del ranking por distancia |

Detalles operativos:

1. **Comando Artisan por fuente** (`php artisan precios:sync walmart --dry-run`)
   actuando como Price Provider: obtiene → valida → escribe **solo a Staging**, jamás
   directo a `precios_actuales` (§6.3).
2. **Convención de origen**: `origen_dato = '{modo}-{fuente}'` → `vtex-walmart`,
   `vtex-maxi-despensa`, `vtex-don-juan`, `html-super-selectos`; `'manual'` queda intacto.
3. **Cortesía HTTP (nuestros valores, más conservadores que los del repo hermano §2.4)**:
   User-Agent identificable `SmartMarketSV-AcademicBot/1.0 (+URL-del-repo; correo-de-contacto)`
   *(completar URL real del repo y contacto institucional antes de la primera corrida)*;
   pausa configurable entre requests con default 1500 ms; reintentos ×3 con backoff
   exponencial solo ante HTTP 429/503; agotados → abortar la corrida completa de esa
   fuente; detección de captcha/bloqueo → abortar sin evasión ni rotación de identidad.
4. **Normalización**: reutilizar `App\Services\NormalizadorTexto`; matching automático:
   alias exacto → fuzzy ≥ 0.85 → alta automática de producto + alias si es nuevo
   (esto ya corresponde al alcance v1.1 que §6.2 dejaba para después).
5. **Health check por corrida**: tabla `sync_runs` compara conteo contra la corrida
   previa; caída brusca ⇒ alertar y no publicar esa fuente (§6.4).
6. **Orden de construcción**: driver VTEX primero (menor fragilidad: JSON limpio);
   Super Selectos (HTML) después, validando los selectores de §2.3 contra un fixture
   fresco capturado antes de confiar en ellos.
7. **PriceSmart no se automatiza**: carga manual (veredicto en §5).

---

## 5. Veredicto legal por fuente (revisión realizada el 2026-08-22)

Metodología: lectura de los Términos y Condiciones publicados por cada dominio (texto
íntegro cuando fue accesible), cada `robots.txt`, y notas corporativas para clasificar
entidades. La confianza indica qué tan directo es el hallazgo.

### Resumen

| Fuente | Entidad detrás | Veredicto | Confianza | Tratamiento |
|---|---|---|---|---|
| Super Selectos | Super Selectos, S.A. de C.V. (Grupo Calleja) — independiente | Sin cláusula anti-automatización; robots.txt permite rastreo general | Alta (texto íntegro leído) | ✅ Automatizar (modo HTML) |
| Walmart SV / Maxi Despensa / Don Juan | Operadora del Sur, S.A. de C.V. (Walmart CA) — una empresa, tres vitrinas | ToS prohíbe explícitamente extracción automatizada (browsewrap); robots.txt NO bloquea catálogo ni `/api/*` | Alta (Walmart, Don Juan: texto verificado) / Media-Alta (Maxi Despensa: inferencia fuerte) | ⚠️ Automatizar con riesgo aceptado (ADR-10) |
| PriceSmart | Pricesmart (club de membresía) | robots.txt prohíbe scrapers por nombre; ToS solo revisado por fragmentos | Media-Alta | ❌ No automatizar — carga manual |

### 5.1 Super Selectos — la única cadena verdaderamente independiente

- ToS: PDF íntegro leído (9 páginas, 80 cláusulas, rev. 2025-12-30, NIT
  0614-110169-101-1): https://admincms.blob.core.windows.net/web/documents/TerminosYCondiciones.pdf
  — cero menciones a scraping o extracción automatizada; las cláusulas 70–76 cubren
  únicamente propiedad intelectual, framing, deeplinking y marcas.
- robots.txt: `Allow: /` explícito; solo bloquea `/cart`, `/account`, `/login`.
- Matices: la cláusula 12 aclara que precios/promociones online pueden diferir de tienda
  física; y el modo HTML (§2.3) sigue siendo el más frágil ante rediseños.

### 5.2 Familia Walmart (Operadora del Sur, S.A. de C.V., NIT 0614-310797-109-0)

- ToS de walmart.com.sv (https://www.walmart.com.sv/terminos-y-condiciones-de-compra):
  prohíbe usar herramientas automatizadas de extracción de datos; entre los usos
  indebidos figura *"recopilar y utilizar las descripciones de los productos"*; prohíbe
  navegar mediante spiders/robots/agentes automáticos. Es browsewrap (términos
  publicados en el sitio, aceptados por su uso).
- La Despensa de Don Juan
  (https://www.ladespensadedonjuan.com.sv/terminos-y-condiciones-de-compra): texto
  verificado idéntico al de walmart.com.sv; su FAQ confirma operación compartida.
- Maxi Despensa: sin página ToS propia hallada con cláusula textual anti-extracción
  (su página de términos trata cancelaciones/devoluciones y cita procesos de Bodegas
  Centroamérica); se clasifica por inferencia fuerte: misma entidad operadora y stack
  VTEX, lanzamiento anunciado por Walmart CA en julio 2024
  (https://www.walmartcentroamerica.com/noticias/2024/07/maxi-despensa-lanza-nuevo-sitio-para-compras-en-linea).
- Contrapeso objetivo: los robots.txt de los tres dominios comparten plantilla VTEX y
  NO bloquean las URLs de catálogo ni `/api/catalog_system/*`; publican sitemaps.
- Tensión reconocida: robots.txt permisivo con el catálogo vs ToS restrictivo. La
  decisión de automatizar igualmente es una aceptación informada de riesgo — no un
  vacío inadvertido — formalizada en ADR-10.

### 5.3 PriceSmart — fuera de la automatización

- robots.txt (https://www.pricesmart.com/robots.txt): sección titulada *"Complete
  blocking of AI training bots and scrapers"* que bloquea por nombre a `Scrapy`
  (`Disallow: /`) junto a los bots de entrenamiento de IA, permitiendo explícitamente
  buscadores y bots de búsqueda con IA.
- ToS (https://www.pricesmart.com/es-co/terminos-y-condiciones; plantilla común a todos
  los países): fragmentos revisados sin cláusula anti-extracción visible, pero texto
  íntegro pendiente de verificación exhaustiva.
- Única fuente cuyo dueño declaró intención específica contra herramientas de scraping:
  se respeta esa línea explícita. Permanece como tercera cadena vía carga manual
  (ya sembrada en `shared/demo_products.json`). Respetar esta exclusión es parte de lo
  que hace defendible el ADR-10 para las demás fuentes.

### 5.4 Matices transversales

- **Browsewrap** tiene exigibilidad débil frente a un clickwrap, pero constituye aviso
  de voluntad del dueño: el riesgo residual es civil-comercial (abuso/sobrecarga del
  servicio), no penal, y se neutraliza operativamente con cortesía estricta (§4 punto 3).
- **Datos fácticos vs contenido creativo:** precios, nombres comerciales, unidades y
  disponibilidad son datos fácticos; imágenes y textos promocionales son contenido
  creativo que no recolectamos ni mostramos (política §4).
- **Apagado instantáneo:** cada fuente tiene interruptor propio en
  `config/price_providers.php`; desactivar una no afecta al resto (principio de
  intercambiabilidad, §6.1 de `02-arquitectura.md`). Ante cualquier solicitud de un
  titular, la respuesta es apagar la fuente y atenderlo.
