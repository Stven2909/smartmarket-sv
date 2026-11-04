# HU-22 — Identificación determinista de reglas, sin cambiar el contrato Laravel

## Objetivo

El campo `version_reglas` identifica una versión declarada, pero una modificación de `data/rules.json` puede ocurrir sin que se incremente ese valor. Para permitir auditoría real de cada inferencia, el servicio calcula un **SHA-256 semántico** de las reglas efectivamente validadas.

## Cómo se obtiene

1. Carga las reglas mediante `load_rules()`, con el parser y validaciones que usa la inferencia.
2. Ordena las reglas por ID y serializa sus atributos como JSON canónico, sin depender de saltos de línea, espacios ni orden de claves del archivo.
3. Calcula SHA-256 de los bytes UTF-8 resultantes.
4. Almacena ese resultado en caché del proceso. No crea temporizadores, tareas en background, bases de datos ni llamadas externas.

No es una firma digital ni autentica al emisor: identifica el contenido de las reglas para comparaciones técnicas. La huella se renueva al desplegar/reiniciar el proceso con una nueva base de reglas; las instalaciones deben reiniciarse al cambiar el archivo.

## Cabecera HTTP opcional y retrocompatible

Las respuestas correctas tienen la siguiente cabecera (valor ilustrativo):

```http
X-Expert-Rules-SHA256: <64 caracteres hexadecimales>
```

Disponible en `POST /api/v1/recommend`, `GET /api/v1/knowledge` y `GET /ready`. El cuerpo de `/api/v1/recommend` continúa con **16 campos**, sin cambios de nombres ni de comportamiento, y recibe los mismos **14 hechos**. Laravel puede ignorar la cabecera y seguir funcionando; si se desea trazabilidad completa de extremo a extremo, el compañero podrá guardar este metadato opcionalmente en su lado.

## Manejo de fallos

Si la base de conocimiento no se puede cargar o validar, `/api/v1/recommend` responde HTTP 503 con un error genérico. No expone nombres de archivos privados. La disponibilidad básica `/health` sigue pública, liviana y no depende de las reglas.

## Comprobaciones

```bash
ruff check app demo scripts tests
pytest -q tests/test_rules_fingerprint.py
pytest -q
```

Las pruebas comprueban repetibilidad, que un cambio de prioridad cambie el SHA, independencia del orden de las reglas, coincidencia de las tres cabeceras, inexistencia de campos JSON adicionales, errores 422 para entradas inválidas y 503 ante reglas indisponibles.

**Límites:** la huella no prueba que los datos enviados por Laravel reflejen precios correctos ni sustituye un test de integración extremo a extremo. No se modifica `develop` ni la rama Python del compañero desde esta historia.
