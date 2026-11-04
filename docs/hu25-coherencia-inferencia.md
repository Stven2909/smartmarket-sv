# HU-25 — Verificación independiente de coherencia del sistema experto

## Objetivo

La auditoría de coherencia comprueba automáticamente que cada respuesta de `POST /api/v1/recommend` sea compatible con los hechos recibidos y la base de reglas vigente. Detecta contradicciones sin alterar la inferencia y sin introducir latencia adicional en las peticiones de producción.

Se ejecuta desde `scripts/check_inference_consistency.py` y se prueba en `tests/test_inference_consistency.py`. La API **no importa ni ejecuta** este verificador durante una recomendación normal, de modo que no aumenta el consumo cuando el servicio está inactivo.

## Invariantes comprobados

- Se devuelve el mismo `request_id` de la solicitud y exactamente los hechos derivados del clasificador.
- La `trace` contiene las 8 reglas, en el orden estable por ID, con las mismas condiciones que el JSON validado. Cada `actual`, `expected` y `matched` corresponde a un hecho y una condición real.
- Las condiciones coincidentes y las pendientes forman la partición correcta. El estado `activated` y su motivo concuerdan con esa evaluación.
- `reglas_activadas` coincide con las activaciones de la traza; `winning_rule` se obtiene por prioridad e ID; `losing_rules` respeta el orden de resolución de conflictos.
- Si existe regla ganadora, `nivel_recomendacion`, `accion_sugerida`, `prioridad_aplicada` y el comienzo de `explicacion` corresponden exactamente a esa regla.
- Si una regla crítica R01–R05 está activa, no se devuelve un dictamen positivo. Cuando ninguna regla se activa, la decisión sigue siendo provisional `NO_RECOMENDABLE` y no se inventa una ganadora.
- El índice auxiliar, su clasificación, los componentes y los pesos coinciden con el cálculo determinista esperado. No sustituyen la evaluación de reglas críticas.

## Alcance de las pruebas

La suite revisa los escenarios documentados, una muestra determinista de 200 combinaciones tomadas de la grilla representativa, las decisiones R01–R08 y el caso sin regla. También modifica intencionalmente cada campo relevante de una respuesta, así como las condiciones de una traza, para confirmar que el verificador denuncia las inconsistencias.

```bash
pytest -q tests/test_inference_consistency.py
ruff check app demo scripts tests
pytest -q
```

Este test no constituye evidencia de que Laravel calcule precios correctos o que la infraestructura de Streamlit Cloud esté disponible. Se siguen probando esas responsabilidades por separado. **No se modifica `develop` del compañero**, sus endpoints, el contrato de 14 campos de entrada ni los 16 de salida.
