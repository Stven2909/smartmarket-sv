# Procedencia y captura de datos — SmartMarket SV

## Alcance del prototipo

El sistema admite dos tipos de datos:

| Tipo | Origen | Uso |
|---|---|---|
| **Observación manual real** | Información observada y registrada por integrantes del equipo (por ejemplo, precio visible, disponibilidad observada o promoción en una sucursal) | Construir alternativas de compra, probar decisiones y documentar casos prácticos |
| **Escenario sintético** | Valores inventados deliberadamente para las pruebas | Verificar reglas, casos límite, conflictos, comparaciones y análisis de sensibilidad |

Los escenarios incorporados en `data/scenarios.json` son **sintéticos**. No deben presentarse como registros observados en establecimientos reales. La entrada manual de datos tampoco implica que la disponibilidad siga vigente después de la observación.

No se utiliza web scraping, extracción automatizada de portales de supermercados, integración con inventarios comerciales ni servicios de precios en tiempo real.

## Registro recomendado de observaciones reales

El equipo puede utilizar `data/plantilla-captura-manual.csv` para registrar datos por producto. El archivo de plantilla **solo contiene encabezados**: no incluye registros reales ni ficticios.

| Campo | Descripción |
|---|---|
| `registro_id` | Identificador local del registro |
| `fecha_observacion` | Fecha y hora de la observación, con zona horaria |
| `procedencia` | `manual_real` o `sintetico` |
| `establecimiento` / `sucursal` | Lugar observado, si corresponde |
| `producto` / `unidad` | Descripción y unidad de comparación |
| `moneda` | Moneda del precio, por ejemplo USD |
| `precio_regular` / `precio_final` | Valores registrados; vacíos si son desconocidos |
| `promocion_observada` / `disponibilidad_observada` | `si`, `no` o `desconocido` |
| `metodo` | Por ejemplo, `visita`, `consulta_manual` o `escenario` |
| `observaciones` | Aclaraciones sobre condiciones, cantidad, vigencia o incertidumbre |

Registrar **desconocido** cuando no se haya verificado algún aspecto. No convertir información ausente en una supuesta disponibilidad, oferta o descuento.

## De los datos al motor experto

El servicio Python **no recibe el listado de precios por producto**. Recibe los 14 hechos agregados de `RecommendationRequest` en `POST /api/v1/recommend`: presupuesto, costo total, ahorro, distancias, tiempo, conteos de disponibilidad, cantidad de supermercados y presencia de promociones, además de los IDs de solicitud y alternativa.

Para construir una alternativa desde registros manuales:

1. Definir una lista de compra y su presupuesto.
2. Sumar costos de artículos con precio conocido según cantidades y unidades comparables.
3. Calcular por separado la cantidad de artículos disponibles y esenciales disponibles; no convertir ausencia de precio en disponibilidad confirmada.
4. Definir distancia y tiempo como observaciones o supuestos explícitos. Si son estimaciones, identificarlos como tales en el registro de evidencia.
5. Determinar el ahorro respecto de una referencia documentada y usar la misma definición para todas las alternativas comparadas.
6. Formar el JSON con las 14 propiedades obligatorias y validarlo antes de llamar a la API.

**Importante:** no se deben mezclar totales parcialmente conocidos con una supuesta lista completa. La API validará conteos imposibles, pero no puede comprobar si los precios manuales se recogieron correctamente.

## Trazabilidad y compatibilidad

La procedencia, fecha y descripción de la captura deben conservarse **en un registro externo a la solicitud HTTP**. Agregar `procedencia` u otros metadatos dentro de `/api/v1/recommend` devolvería HTTP 422 porque el contrato actual prohíbe campos adicionales.

Las pruebas automáticas pueden verificar el procesamiento determinista de los hechos y las restricciones del contrato. No certifican la veracidad de los datos introducidos ni la exactitud del mercado. La evaluación académica definida para el prototipo es interna y reproducible: casos de prueba, límites, conflictos de reglas y sensibilidad de las decisiones, sin obligación de acudir a especialistas externos.
