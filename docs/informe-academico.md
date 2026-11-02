# HU-12: Informe académico PDF de evidencia técnica

El servicio Python puede generar un documento descargable que reúne los resultados técnicos de **2 a 10 alternativas**. No modifica las reglas ni duplica el algoritmo de inferencia; utiliza los mismos servicios de recomendación, comparación, auditoría y sensibilidad que ya ofrece FastAPI.

## Contenido del documento

1. Portada con fecha y hora UTC, versiones del contrato, reglas, clasificador e índice.
2. Resumen de dictámenes y número de conflictos y casos sin regla ganadora.
3. Ranking explicable, con las advertencias de comparabilidad.
4. Matriz de cobertura R01–R08: activaciones y victorias en los escenarios suministrados.
5. Auditoría de consistencia: hallazgos, solapamientos, clases de prueba y prioridades aplicadas.
6. Umbrales y pesos del índice de conveniencia.
7. Por cada alternativa: hechos de entrada, explicación, acción, regla ganadora, traza completa de ocho reglas, aportes ponderados y análisis de sensibilidad.
8. Alcance y limitaciones metodológicas.

Las tablas utilizan encabezados repetidos al dividirse entre páginas. El PDF incluye paginación y puede consultarse sin ejecutar Streamlit.

## Contrato opcional

`POST /api/v1/evidence-report` recibe una solicitud JSON:

```json
{
  "procedencia": "sintetico",
  "escenarios": [
    {
      "nombre": "Alternativa A",
      "hechos": {
        "request_id": "eval-1",
        "alternativa_id": "a",
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
    },
    {
      "nombre": "Alternativa B",
      "hechos": {
        "request_id": "eval-2",
        "alternativa_id": "b",
        "costo_total": 56.00,
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
    }
  ]
}
```

`procedencia` admite `sintetico` y `no_verificada`, siendo `no_verificada` el valor por defecto. **Es una declaración del solicitante, no una verificación de autenticidad de datos.** La demo Streamlit indica explícitamente `sintetico` para los nueve escenarios de ejemplo.

Las alternativas requieren presupuesto común e identificadores únicos. Los hechos deben pasar la validación original de `RecommendationRequest`. Entradas incompletas, grupos de tamaño inválido o presupuestos distintos reciben HTTP 422.

La respuesta correcta es un archivo binario `application/pdf`, con cabecera de descarga y `Cache-Control: no-store`. Si está configurada `SMARTMARKET_API_KEY`, se exige `X-API-Key` igual que en las demás rutas protegidas. El endpoint no escribe el documento en una base de datos ni en el sistema de archivos.

## Uso desde Streamlit

Abre **Base de conocimiento**, desciende hasta **Informe académico descargable**, ejecuta **Generar informe académico PDF** y utiliza **Descargar informe académico PDF**.

La interfaz transmite los nueve escenarios precargados y descarga el documento que genera FastAPI. No se requiere Laravel. Los hechos se conservan íntegros; no se inventan cifras.

## Pruebas de aceptación

```bash
python -m pytest -q tests/test_evidence_report.py
python -m pytest -q
ruff check app demo tests
```

Las pruebas comprueban que:

- El PDF contiene las secciones, escenarios, trazas y análisis de sensibilidad esperados.
- Su estructura puede abrirse con un lector PDF y se reparte en varias páginas.
- Se preservan los 14 campos de entrada y 16 campos de salida de la recomendación original.
- El endpoint devuelve el tipo MIME y cabeceras correctos y aplica la API key.
- La interfaz de Streamlit obtiene realmente el PDF mediante una llamada HTTP simulada a FastAPI con ASGITransport.
- Los grupos incompletos, duplicados o incomparables se rechazan sin alterar reglas.

## Limitaciones

La auditoría usa 2430 escenarios **sintéticos representativos** y no constituye verificación exhaustiva del mercado. El análisis de sensibilidad expresa variaciones hipotéticas, no probabilidades ni predicciones de precios. Este informe no sustituye una evaluación de exactitud comercial ni implica que los datos suministrados provengan de supermercados reales. El sistema experto Python mantiene su responsabilidad única: inferir y explicar a partir de hechos recibidos.
