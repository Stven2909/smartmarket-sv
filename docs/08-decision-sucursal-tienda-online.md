# ADR-11: Sucursal "Tienda en línea" — coordenadas nulas y exclusión del ranking físico

**Estado:** Aceptado — decisión del equipo, 2026-08-22
**Contexto técnico:** Extractor automático de precios, Fase 1 (`06-referencia-extractor-vtex.md` §4)
**Nota de numeración:** los ADRs 001–009 viven en `02-arquitectura.md` §9; **ADR-10** es
`07-decision-extractor-fuentes-riesgo.md`; este documento es **ADR-11**.

---

## Contexto

El extractor automático trae precios del canal e-commerce de cada supermercado. Ese canal
no tiene una ubicación física única en el mapa: la Sucursal "Tienda en línea" representa
entrega nacional. El esquema actual exige `sucursales.latitud/longitud NOT NULL`, lo que
obligaría a inventar coordenadas (p. ej. la casa matriz) — un dato falso que contaminaría
el cálculo Haversine y el ranking por cercanía.

Además existía un bug latente esperando suceder: `ComparisonService` casteaba las
coordenadas con `(float) $sucursal->latitud` — con null eso produce silenciosamente
`0.0`, ubicando la tienda en el golfo de Guinea (lat 0, lng 0).

## Decisión

1. `sucursales.latitud/longitud` pasan a **nullable**.
2. Todo supermercado que opere por canal online obtiene una Sucursal identificada como
   "Tienda en línea" con coordenadas nulas.
3. Las alternativas sin coordenadas quedan **excluidas del ranking de cercanía física**
   (Haversine / geoespacial): no tienen `distancia_km`, `tiempo_minutos` ni
   `costo_tiempo`, y quedan fuera de la normalización min-max de
   `PenalizacionDistancia`.
4. Siguen siendo **totalmente válidas como fuentes para la comparación de precios a
   nivel nacional**: participan del costo_total, beneficios de promociones,
   disponibilidad y del Score (con `penalizacion_distancia = 0`).
5. En `resultados_optimizacion`, `distancia` y `tiempo` pasan a nullable: si la mejor
   opción es una tienda online se persiste null en lugar de fingir valores.

## Implementación

| Pieza | Cambio |
|---|---|
| Migración | `2026_08_22_120001_make_sucursales_coordenadas_nullable` |
| Migración | `2026_08_22_120004_make_resultados_distancia_tiempo_nullable` |
| `ComparisonService` | Propaga `null` cuando no hay coordenadas (antes casteaba a float) |
| `OptimizationService` | Salta Haversine para alternativas sin coords; las excluye del min/max; penalización 0; persistencia nullable |

## Consecuencias

- ✅ El canal online puede entrar al comparador sin datos geográficos falsos.
- ✅ La comparación de precios nacionales sigue funcionando íntegra para esas tiendas.
- ⚠️ El frontend debe tratar `latitud/longitud/distancia_km/tiempo_minutos` nulos como
  "sin marcador en el mapa" (relevante solo cuando existan tiendas online sembradas).
- ⚠️ Si TODAS las alternativas carecen de coordenadas, la normalización queda vacía y
  todas reciben penalización 0 — el ranking pasa a decidirse por costo/promociones,
  que es el comportamiento correcto para ese escenario.

## Referencias

- `02-arquitectura.md` §5.1 (fórmula del Score), ERD v1.0 Nivel 1 (`Sucursal`).
- `07-decision-extractor-fuentes-riesgo.md` (ADR-10) — origen de este cambio.
