# HU-15 y HU-16 — Importación de alternativas y pruebas de propiedades

## Objetivo

**HU-15:** permitir que quien exponga o investigue SmartMarket SV cargue alternativas de compra preparadas manualmente en CSV o JSON, valide sus hechos, examine la procedencia y compare casos desde el laboratorio de Streamlit.

**HU-16:** reforzar la lógica R01–R08 con pruebas generativas y metamórficas para descubrir incoherencias, cambios de resultados por orden de reglas y comportamientos inesperados de los límites.

La importación es **exclusiva de Streamlit**: no modifica el endpoint de FastAPI, no incorpora scraping ni nuevas responsabilidades para Laravel. Los 14 hechos enviados a `/api/v1/compare` son exactamente los mismos.

## CSV de exposición disponibles

### 1. Catálogo de referencias web (`data/precios_referencia_web_expo.csv`)

Se guardaron **61 referencias de productos** visibles en catálogos públicos de **Súper Selectos** y **Walmart El Salvador**, con precio mostrado en USD, categoría, enlace, fecha de consulta y advertencia sobre su alcance.

Fuentes verificadas a nivel de páginas de categoría:

- [Súper Selectos: granos básicos](https://www.superselectos.com/products?category=033)
- [Súper Selectos: detergentes](https://www.superselectos.com/products?category=077228)
- [Súper Selectos: canasta](https://www.superselectos.com/products-landing/CANASTA0606)
- [Walmart El Salvador: lácteos](https://www.walmart.com.sv/Lacteos)

**El catálogo contiene precios de referencia web publicados, no precios confirmados de una sucursal, disponibilidad garantizada ni datos en tiempo real.** Es un archivo informativo, no se importa directamente al comparador, porque una línea de producto individual no cumple los 14 hechos de una alternativa de compra.

### 2. Alternativas sintéticas para la exposición (`data/escenarios_exposicion_300.csv`)

El archivo contiene **300 casos de prueba**, organizados en **15 listas de 20 alternativas** cada una. Cada lista conserva el mismo presupuesto, número total de productos y cantidad de esenciales para permitir comparaciones coherentes. Cada caso tiene sus 14 hechos completos, más metadatos opcionales:

| Campo de metadatos | Uso |
|---|---|
| `nombre` | Etiqueta legible para la exposición |
| `procedencia` | `sintetico`, `manual_real` o `mixto_referencia_web` |
| `fecha_observacion` | Fecha declarada para la fuente o captura |
| `fuente_url` | URL HTTPS de apoyo cuando corresponda |
| `tienda` | Tienda declarada o ficticia |
| `notas` | Alcance, advertencias y supuestos |

Los costos de muestra se construyeron alrededor de conjuntos de precios publicados, con **ajustes hipotéticos claramente declarados**. Distancias, tiempos, inventarios, promociones y ahorros fueron simulados para probar distintas reglas. El conjunto se etiqueta `sintetico`; **no presenta ninguna lista completa como cotización real de un supermercado**.

En la columna `notas` aparece el costo base formado por referencias y la variación hipotética empleada. Los enlaces permiten revisar el origen de las referencias de productos, pero **no corroboran los demás hechos simulados**.

## Uso de la importación

1. Abrir la demo Streamlit y seleccionar **Comparador**.
2. En **Origen de las alternativas**, escoger **Archivo CSV/JSON**.
3. Cargar `data/escenarios_exposicion_300.csv` o un archivo propio.
4. Verificar el recuento, procedencia y tabla de validación.
5. Seleccionar de **2 a 10 alternativas** con el mismo presupuesto y hacer clic en **Comparar alternativas**. Para una demo rápida, seleccionar tres alternativas de la **Lista 01**, que comparten el presupuesto.

Al abrir la aplicación o cargar el CSV **no se llama a Render**. La API se consulta únicamente cuando se pulsa **Comparar alternativas**. Se rechaza el archivo completo si una fila es inválida: no se aceptan silenciosamente datos parciales.

## Reglas de validación

- Máximo **2 MB** y **750 filas** por archivo, UTF-8.
- Los 14 campos de `RecommendationRequest` son obligatorios y se envían sin los metadatos.
- Los números deben ser finitos, no negativos; el presupuesto es positivo.
- Los conteos de productos y esenciales tienen límites coherentes; las cantidades son enteras.
- Los booleanos admiten `true/false`, `sí/no` o `1/0`.
- Los IDs no pueden repetirse.
- `manual_real` requiere nombre de tienda y fecha; son datos **declarados**, no autentificados.
- `mixto_referencia_web` requiere fecha y fuente HTTPS.
- Si hay presupuestos diferentes, el sistema lo advierte y el comparador impide una selección no comparable.
- No se retiene un archivo en el servidor de Render; el documento cargado se procesa dentro de la sesión Streamlit.

## HU-16: pruebas de propiedades

Las pruebas en `tests/test_property_invariants.py` usan **Hypothesis** exclusivamente en el entorno de desarrollo y GitHub CI, sin instalarlo en Render ni Streamlit. Generan alternativas válidas para verificar:

- Determinismo de nivel, traza y explicación sobre hechos idénticos.
- Exclusión mutua de regiones de presupuesto, ahorro, distancia, tiempo, productos y supermercados.
- Prioridad de reglas críticas: un riesgo activado no produce una recomendación favorable.
- Invariancia del dictamen y la regla ganadora al reordenar las reglas.
- Activación de R01 al superar el límite del 10 % y R02 cuando falta un esencial.
- Monotonía del índice auxiliar frente a más distancia, más ahorro y promociones, manteniendo los demás hechos constantes.
- Equivalencia de los dictámenes después de serializar y deserializar la solicitud JSON.

La suite usa semillas reproducibles y minimiza los ejemplos que fallan. Las propiedades verifican invariantes **definidos**, no garantizan que los umbrales sean óptimos comercialmente.

## Verificación local

```bash
python -m pip install -r requirements-dev.txt ruff
ruff check app demo scripts tests
python -m pytest -q tests/test_manual_dataset.py tests/test_expo_datasets.py
python -m pytest -q tests/test_property_invariants.py
python -m pytest -q
```

## Límites de la investigación

No hemos usado scraping automatizado. Las referencias se seleccionaron de páginas públicas para construir el catálogo documental. Sus precios pueden cambiar y no deben anunciarse como promociones vigentes ni como inventario confirmado. El conjunto de 300 casos es una **simulación académica**, útil para probar el motor y mostrar sus respuestas, no para comparar establecimientos reales en tiempo real.
