# SmartMarket SV — Contexto del Proyecto (para retomar en desarrollo)

> **Qué es este documento:** un resumen ejecutivo de todo lo definido hasta ahora, pensado para
> pegarse al inicio de una nueva conversación centrada en el desarrollo (código, migraciones,
> endpoints, etc.), sin tener que repetir todo el proceso de diseño. Los ocho documentos
> completos (`01` a `08`) ya existen y son la fuente de verdad — esto es el mapa para navegarlos
> rápido y no perder decisiones ya tomadas.

**Estado actual:** los 8 documentos están terminados y compartidos con el equipo. El repositorio
de GitHub ya está creado. Lo que sigue es diseño detallado (wireframes, OpenAPI) y construcción.

---

## 1. Qué es SmartMarket SV (una línea)

Plataforma web/PWA que ayuda a familias salvadoreñas a planificar sus compras de supermercado,
comparando precios, promociones y ubicación de forma neutral, optimizando el presupuesto mediante
algoritmos propios y un Sistema Experto de reglas — sin depender de IA generativa para funcionar.

**Por qué existe:** el costo de la Canasta Básica Alimentaria en El Salvador ha subido de forma
sostenida (de ~$200 en 2019 a más de $256 en 2026), y no existe una herramienta local que
centralice precios entre supermercados como sí existe en Chile (Carriapp), Argentina
(Tu-Alacena) o España (FindIt/OCU Market). Detalle completo, fuentes y cifras en
`01-vision-negocio.md` (el ensayo de Emprendedurismo).

---

## 2. Los 8 documentos y qué contiene cada uno

| Documento | Audiencia | Contenido clave |
|---|---|---|
| `01-vision-negocio.md` (ensayo Word) | Profesor de Emprendedurismo | Problema, contexto (datos de canasta básica/inflación con fuentes reales), objetivos, revisión de literatura (casos internacionales + teorías de Simon/Kotler/Ishikawa), causas raíz, módulos del producto, modelo de negocio, escalabilidad (V1/V2/V3), conclusiones. **No menciona microservicios, Docker, ADRs — lenguaje de negocio.** |
| `02-arquitectura.md` | Todo el equipo técnico | Principios de arquitectura (8), stack completo, arquitectura general, **2 flujos end-to-end**, módulos clasificados (Core/Apoyo/Externos), pipeline de datos (Price Providers → Staging → Normalización → Validación → Catálogo), Motor de Normalización, Sistema Experto (resumen), seguridad, testing, **No-objetivos**, riesgos, **ADRs numerados (001-009)**, **ERD v1.0 completo con diagramas e imágenes** (`erd_nivel1_core.png`, `erd_nivel2_pipeline.png`), estado del proyecto. **Documento congelado — cualquier cambio de fondo necesita un ADR nuevo.** |
| `03-plan-implementacion.md` | Equipo (operativo, sí puede cambiar) | Organización en Track A (Laravel/React) y Track B (Sistema Experto/Python), roadmap por fases (0A/0B → 1-9), fases del Sistema Experto (P0-P4), Definition of Done, tabla de riesgos, roadmap futuro (v1.1/v1.2), estructura de carpetas del repo. |
| `04-sistema-experto.md` | Materia de Sistemas Expertos + equipo | Dominio, hechos primarios vs. derivados, variables de salida, **Forward Chaining** (con justificación), **política de resolución de conflictos** (jerarquía de prioridad), 15 reglas derivadas por escenario, **explicabilidad a dos niveles** (reglas activadas + explicación en lenguaje natural), contrato de API con errores (400/422/500), casos de prueba (incluyendo uno ambiguo), limitaciones. Framework de Python **todavía pendiente de confirmar** (candidatos: PyKnow, CLIPS/clipspy, Durable Rules). |
| `05-decision-costo-combustible.md` | Todo el equipo técnico | **ADR-05**: reemplazo de `CostoCombustible ($)` por `PenalizacionDistancia` normalizada (0–1, min-max por corrida) en la fórmula del motor de optimización — evita dolarizar combustible encadenando distancia Haversine × precio citado × consumo supuesto (tres capas de imprecisión). Justificación, fórmula antes/después, migraciones, implementación backend/frontend y suite de regresión. |
| `06-referencia-extractor-vtex.md` | Equipo técnico (extractor en curso) | Análisis de referencia del extractor automático de precios (repo hermano): fuentes y modos (HTML/VTEX/partner-feed), estrategia VTEX paso a paso, cortesía HTTP, normalización, persistencia append-only, crons; mapeo a nuestro pipeline. **§4: plan aprobado Fases 0–3; §5: veredicto legal por supermercado con citas y URLs. En implementación desde el 2026-08-22.** |
| `07-decision-extractor-fuentes-riesgo.md` | Todo el equipo técnico | **ADR-10**: alcance de la extracción automatizada — se automatizan Super Selectos (HTML) y las tres tiendas VTEX de Walmart CA con riesgo académico aceptado e informado; PriceSmart queda en carga manual (su robots.txt prohíbe scrapers por nombre). Condiciones operativas obligatorias: UA identificable, pausas, sin evasión de controles, apagado instantáneo por config, solo datos fácticos (sin imágenes ni logos). |
| `08-decision-sucursal-tienda-online.md` | Todo el equipo técnico | **ADR-11**: `sucursales.latitud/longitud` pasan a nullable para la Sucursal "Tienda en línea" (canal nacional sin ubicación física) — esas alternativas quedan excluidas del ranking Haversine pero siguen válidas para comparación de precios nacional; también hace nullable `distancia/tiempo` en `resultados_optimizacion` y corrige el cast `(float) null → 0.0` en `ComparisonService`. |

---

## 3. Decisiones arquitectónicas clave (ADR — ya congeladas en `02-arquitectura.md`)

| ADR | Decisión |
|---|---|
| 001 | Laravel 12 como backend (el equipo ya lo domina) |
| 002 | React + PWA como frontend (cubre Android/iOS/escritorio sin apps nativas) |
| 003 | PostgreSQL como base de datos |
| 004 | Laravel Sanctum como única estrategia de autenticación (se descartó JWT manual, Passport y Firebase) |
| 005 | Arquitectura por capas: Controller → Service → Model |
| 006 | Pipeline de datos desacoplado: cualquier fuente de precios (manual, scraping, API, CSV) pasa por Staging → Normalización → Validación antes de tocar el Catálogo Maestro |
| 007 | Motor de Normalización como módulo propio (no solo un paso genérico del pipeline) |
| 008 | Score del Motor de Optimización configurable: `Score = α·CostoCompra + β·PenalizacionDistancia + γ·CostoTiempo − δ·BeneficioPromociones` (menor Score = mejor opción; los pesos α/β/γ/δ no están fijos en el código) |
| 009 | Sistema Experto **stateless**: nunca accede directamente a PostgreSQL, solo recibe hechos en JSON desde Laravel y responde una recomendación en JSON. Laravel es el único dueño de la base de datos. |

**Principios de arquitectura (resumen, los 8 completos están en `02-arquitectura.md` sección 1):**
el núcleo no depende de una tecnología específica; cada módulo tiene una única responsabilidad;
las integraciones externas son intercambiables; el sistema sigue funcionando si falla un servicio
opcional (Sistema Experto o IA); el MVP prioriza simplicidad; la IA generativa es un
complementario, no un requisito; ninguna fuente externa modifica el Catálogo Maestro sin pasar por
validación; las reglas de negocio son configurables, no hardcodeadas.

---

## 4. Arquitectura general (resumen visual)

```
React (PWA) → Laravel (orquestador central) → PostgreSQL / Redis / Filament (panel admin)
                     │
                     │ HTTP (JSON) — Laravel nunca envía SQL ni IDs internos, solo hechos
                     ▼
              Sistema Experto (Python, stateless)
                     │
                     ▼ (opcional, solo explica, nunca decide)
              IA Generativa (opcional, v1.2+)
```

**Flujo 1 (consulta):** Usuario → React → Laravel consulta PrecioActual/ListaCompra →
OptimizationService calcula Score → ResultadoOptimizacion → POST a Sistema Experto → Recomendacion
→ React muestra 🟢🟡🔴 + explicación.

**Flujo 2 (datos):** Price Provider → ProductoRaw (staging) → Motor de Normalización → Validación
→ (válido→Catálogo Maestro / inválido→Revisión Manual) → PrecioActual → HistorialPrecio.

---

## 5. Modelo de datos (ERD v1.0 — congelado, ver imágenes en `02-arquitectura.md`)

**Nivel 1 (Core):** `Usuario` (con rol enum), `Categoria`, `Producto` (Catálogo Maestro),
`AliasProducto`, `Supermercado` (sin coordenadas), `Sucursal` (con coordenadas — aquí sí vive la
ubicación física), `PrecioActual` (lo que el comparador siempre consulta), `HistorialPrecio`
(append-only), `ListaCompra`, `ListaCompraDetalle` (con `esencial` y `permite_sustituto` para v2).

**Nivel 2 (Pipeline + Sistema Experto):** `ProductoRaw` (staging, con estado enum: PENDIENTE /
NORMALIZADO / VALIDADO / PUBLICADO / ERROR / REVISION_MANUAL), `ResultadoOptimizacion` (con
`resultado_json` para el detalle si se divide la compra), `Recomendacion` (Python nunca sabe que
existe — la llena Laravel), `SistemaExpertoLog`.

**Fuera de v1.0 a propósito:** Favoritos, HistorialBusqueda, Notificaciones, Publicidad, Cupones,
Suscripciones. (Las promociones **sí** están cubiertas en v1.0 — viven como campos dentro de
`PrecioActual`/`HistorialPrecio`, no como tabla propia; ver aclaración en sección 12.4 de
`02-arquitectura.md`).

---

## 6. Sistema Experto — resumen para retomar directo en código

- **Hechos primarios:** precio, promocion_activa, distancia_km, productos_disponibles, presupuesto.
- **Hechos derivados (calculados por Laravel):** costo_total, ahorro, distancia_adicional,
  tiempo_estimado, numero_supermercados, **score**.
- **Estrategia:** Forward Chaining (parte de hechos conocidos, no de una hipótesis).
- **Resolución de conflictos (por prioridad):** 1) Presupuesto, 2) Disponibilidad, 3) Tiempo/distancia,
  4) Ahorro, 5) Promociones.
- **15 reglas base** ya definidas en `04-sistema-experto.md` sección 7 (R1-R15), cubriendo
  disponibilidad, presupuesto, distancia, promociones, división de compra, tiempo y ahorro.
- **Salida:** `nivel_recomendacion` (🟢/🟡/🔴), `explicacion` (lenguaje natural),
  `accion_sugerida`, `reglas_activadas` (uso interno/depuración).
- **Framework Python:** aún sin confirmar (candidatos: PyKnow, CLIPS vía `clipspy`, Durable
  Rules). No bloquea el resto del diseño.

**Pendiente conocido (no bloqueante):** el ERD agregó `esencial` a `ListaCompraDetalle`, pero el
contrato JSON de `04-sistema-experto.md` todavía no separa `productos_disponibles` en
`productos_esenciales_disponibles` / `productos_opcionales_disponibles`. Falta actualizar ese
documento para que el campo `esencial` realmente se use en las reglas.

---

## 7. Plan de implementación — resumen para arrancar sprints

**Dos tracks en paralelo:**
- **Track A** (Laravel + React): base de datos/auth → Catálogo Maestro + Normalización + Buscador
  → Comparador de listas → Mapa + Motor de Optimización → Promociones/Historial.
- **Track B** (Sistema Experto, Python): arranca con un servicio "mock" desde la Fase 0B (una vez
  el contrato JSON esté congelado) → P0 diseño del conocimiento → P1 servicio FastAPI básico → P2
  motor de reglas → P3 reglas reales (con datos ya producidos por Track A) → P4 explicaciones.
- **Integración** cuando ambos tracks convergen: Laravel llama a Python con datos reales.

**Reglas del equipo:**
- Contrato JSON debe congelarse en la Fase 0B antes de que React empiece con datos "reales" (puede
  empezar antes con wireframes/mocks simples).
- CI/CD, Docker, OpenAPI completo, logging avanzado → categoría "calidad", no bloquean el MVP.
- **Definition of Done** de una tarea: código implementado, sin errores conocidos, probado,
  documentado, revisado por otro integrante, integrado si aplica.

**Estructura de repo ya creada:**
```
smartmarket/
├── docs/  (01 a 08 + erd_nivel1_core.png + erd_nivel2_pipeline.png)
├── backend-laravel/
├── frontend-react/
├── expert-system/       (servicio Python)
├── shared/ (openapi.yaml, demo_products.json, seeders/)
└── README.md
```

---

## 8. Filosofía que debe mantenerse en cualquier decisión futura

Esta conversación pasó por muchas rondas de refinamiento, y el criterio que se mantuvo constante
(y que cualquier nueva conversación de desarrollo debería seguir respetando) es:

1. **El sistema nunca depende de un componente opcional para funcionar** (ni IA generativa, ni
   Sistema Experto, ni una fuente de datos específica).
2. **Priorizar lo que el MVP realmente necesita** sobre lo que "se vería bien" — cada tabla,
   regla o módulo tuvo que justificar su existencia contra el alcance real del semestre.
3. **Las reglas de negocio son configurables, no hardcodeadas**, cuando sea razonable.
4. **Cualquier cambio de fondo a la arquitectura ya congelada (`02-arquitectura.md`) se documenta
   como un ADR nuevo**, no se debate desde cero otra vez.
5. Evitar la "parálisis por análisis": en algún punto de esta conversación se decidió
   explícitamente dejar de refinar y pasar a construir — ese es el punto en el que está el
   proyecto ahora.

---

## 9. Qué sigue (próximos pasos reales)

1. Wireframes de las pantallas principales (buscador, lista, recomendación).
2. Documentar la API en OpenAPI (contrato Laravel ↔ Sistema Experto congelado primero).
3. Migraciones de Laravel a partir del ERD (sección 5 de este resumen / sección 12 de
   `02-arquitectura.md`).
4. Seeders + `demo_products.json` para que todo el equipo trabaje con los mismos datos de prueba.
5. Confirmar el framework de Python para el Sistema Experto y actualizar `04-sistema-experto.md`
   (incluyendo el ajuste de `productos_esenciales_disponibles`/`productos_opcionales_disponibles`
   mencionado en la sección 6 de este resumen).
6. Empezar Sprint 1 según `03-plan-implementacion.md`.

---

## 10. Cómo usar este documento en una nueva conversación

Si retoman el proyecto en otra conversación (por ejemplo, para escribir las migraciones de
Laravel, los modelos Eloquent, o el servicio Python), pueden pegar este documento completo como
mensaje inicial. Da contexto suficiente para:
- No repetir decisiones de arquitectura ya tomadas (están congeladas, sección 3).
- Saber exactamente qué campos tiene cada tabla (sección 5).
- Saber qué reglas ya existen para el Sistema Experto (sección 6).
- Saber en qué orden construir (sección 7).

Si necesitan el detalle completo de alguna sección (por ejemplo, las 15 reglas completas con su
sintaxis `SI...ENTONCES`, o las tablas de riesgos), esos documentos siguen existiendo por
separado (`01` a `04`) y pueden adjuntarse si hace falta más profundidad de la que da este
resumen.
