# ADR-10: Extracción automatizada de fuentes de precios — alcance y aceptación de riesgo académico

**Estado:** Aceptado — decisión del equipo, 2026-08-22
**Contexto técnico:** `06-referencia-extractor-vtex.md` (análisis + veredicto legal por fuente, §5)
**Nota de numeración:** los ADRs 001–009 viven en el registro de `02-arquitectura.md` §9;
esta serie continúa esa numeración. El archivo `05-decision-costo-combustible.md`
corresponde a **ADR-05**; este documento es **ADR-10** (la numeración de archivos en
`docs/` es secuencial e independiente del registro de ADRs).

---

## Contexto

La revisión legal del 2026-08-22 (`06-referencia-extractor-vtex.md` §5) estableció:

| Fuente | Situación legal |
|---|---|
| Super Selectos | Sin cláusula anti-automatización (ToS íntegro leído); robots.txt permisivo |
| Walmart SV / Maxi Despensa / Don Juan | ToS con prohibición textual de extracción automatizada (browsewrap); robots.txt no bloquea catálogo ni `/api/*` |
| PriceSmart | robots.txt prohíbe scrapers por nombre (*"Complete blocking of AI training bots and scrapers"* → `Scrapy: Disallow /`) |

Sin extractor automático, la plataforma depende 100% de carga manual para crecer más
allá del dataset semilla (5 productos), lo que limita cualquier evaluación real del
comparador y del Motor de Optimización.

## Decisión

1. **Se automatizan cuatro fuentes**: Super Selectos (modo HTML) y las tres tiendas
   VTEX de Walmart CA — Walmart SV, Maxi Despensa y La Despensa de Don Juan
   (un solo driver genérico parametrizado por base_url).
2. **PriceSmart queda excluido de la automatización** y permanece como fuente manual.
   Es la única fuente cuyo dueño declaró intención específica contra herramientas de
   scraping; respetar esa línea explícita es parte integral de esta decisión.
3. El conflicto entre el ToS de la familia Walmart y la extracción se **asume como
   riesgo informado y documentado**, justificado por el carácter académico,
   no comercial y de código público del proyecto.

## Justificación

- Proyecto universitario sin fines comerciales: el uso es acotado en volumen,
  finalidad y tiempo comparado con un operador comercial.
- Solo se recolectan **datos fácticos** (precio, nombre comercial, unidad,
  disponibilidad) — nunca contenido creativo (imágenes, textos promocionales, marcas).
- Los robots.txt de las fuentes automatizadas no bloquean el catálogo ni sus APIs
  públicas de lectura; la tensión robots.txt/ToS se reconoce abiertamente en §5.2
  del doc 06, no se oculta.
- La exclusión explícita de PriceSmart demuestra que la decisión respeta la voluntad
  declarada donde existe de forma inequívoca.

## Obligaciones operativas (condiciones de la aceptación)

Estas condiciones NO son opcionales; su incumplimiento invalida este ADR:

1. **User-Agent identificable**: `SmartMarketSV-AcademicBot/1.0 (+URL-del-repo;
   correo-de-contacto)` — completar URL y contacto reales antes de la primera corrida.
   Nunca suplantar un navegador.
2. **Cortesía estricta**: pausa configurable entre requests (default 1500 ms);
   reintentos ×3 con backoff exponencial solo ante 429/503; agotados → abortar la
   corrida completa de esa fuente.
3. **Nunca evadir controles**: captcha o bloqueo detectado ⇒ abortar sin rotar
   identidades, ni resolver desafíos, ni cambiar de red para sortearlos.
4. **Apagado instantáneo por fuente** vía interruptores en
   `config/price_providers.php`; ante solicitud de un titular, se apaga y se atiende.
5. **Trazabilidad completa**: todo lo recolectado pasa por Staging (`producto_raw`
   con `raw_payload`) y llega al catálogo marcado con `origen_dato = '{modo}-{fuente}'`.
6. **Contenido**: cero logotipos corporativos y cero imágenes de producto de las
   tiendas en la UI (iconos genéricos).

## Consecuencias

- ✅ Datos reales suficientes para evaluar comparador, optimizador y Sistema Experto.
- ✅ Riesgo residual documentado y acotado: browsewrap débilmente exigible + patrones
  de cortesía + alcance académico ⇒ exposición principalmente civil-comercial
  (abuso/sobrecarga), mitigada operativamente.
- ⚠️ Persiste un riesgo legal residual asumido por el equipo en las fuentes
  Walmart-family; cualquier cambio de contexto (uso comercial, endurecimiento legal,
  solicitud de cese) obliga a revisar este ADR.

## Reversibilidad

Alta: cada fuente tiene interruptor independiente; desactivarla no afecta al resto
del sistema (ADR-006, pipeline desacoplado). El costo de apagar todas las fuentes
automatizadas es volver a carga manual — estado previo de siempre.

## Referencias

- `06-referencia-extractor-vtex.md` §4 (plan Fases 0–3) y §5 (veredicto legal con citas y URLs).
- `02-arquitectura.md` §6 (pipeline de datos), §9 (registro de ADRs 001–009).
- URLs legales citadas en `06-referencia-extractor-vtex.md` §5.
