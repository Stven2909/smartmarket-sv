# Estabilidad de Streamlit Cloud — diagnóstico y reparación de métricas

Actualizado: 2026-11-03. El error reportado por captura fue:

```text
TypeError: Failed to fetch dynamically imported module:
https://sistema-experto-fork.streamlit.app/~/+/static/js/Metric.*.js
```

La captura muestra que el resultado de la inferencia y la explicación se generaron, pero cuatro indicadores `st.metric` fallaron al cargar su módulo JS. Esto indica un problema de **frontend/carga de recursos**, no demuestra un fallo en las reglas Python. Los recursos JS también pueden fallar temporalmente por caché del navegador, despliegue de frontend, restricciones de red o proxy. Hay incidencias semejantes descritas por usuarios de Streamlit: https://discuss.streamlit.io/t/seeing-typeerror-failed-to-fetch-dynamically-imported-module/92038

## Mejoras del proyecto

1. Se reemplazaron **todos** los usos de `st.metric()` por tarjetas legibles generadas desde el servidor con `st.markdown`, sin importar de forma dinámica el componente `Metric`. Los valores son texto escapado con `html.escape`, evitando inyección HTML, y el diseño CSS usa un grid adaptable a pantallas pequeñas.
2. Se fija `streamlit==1.66.1` en `demo/requirements.txt` para poder probar y desplegar la misma versión del paquete (publicada el 21 de octubre de 2026). Así se evita que `streamlit>=1.55,<2` cambie de versión entre builds.
3. Se conserva el arranque ligero: la interfaz no envía ninguna petición HTTP a Render hasta que el usuario interactúa.
4. Se eliminó el campo editable de URL de la API para evitar que una persona anónima redirija peticiones autenticadas hacia otro dominio. La URL de destino ahora la define el servidor mediante `SMARTMARKET_API_URL` en su entorno o en `st.secrets`. Para usar una API local, el administrador la configura antes de arrancar Streamlit.
5. El cliente HTTP rechaza redirecciones y no envía claves de servicio a orígenes externos con HTTP sin cifrar. Solo se permite HTTP con clave en `localhost`/loopback para desarrollo.
6. La API puede devolver errores o documentos no JSON durante un arranque en frío. La interfaz transforma dichos casos en mensajes de error controlados, sin dejar resultados de una petición previa como si fueran nuevos.
7. La validación del formulario acepta entradas de prueba inválidas sin lanzar excepciones de conversión (`None`, `NaN`, enteros no válidos y texto).

## Despliegue de Streamlit Community Cloud

**El código de GitHub por sí solo no confirma que Streamlit Cloud haya desplegado el commit corregido.**

- En la consola de Community Cloud, confirma que la app usa `HenryBo06/Sistema-experto-fork`, rama `main` y archivo de entrada `demo/streamlit_app.py`.
- Comprueba que en el log de build se instaló `streamlit==1.66.1` desde `demo/requirements.txt`. Al cambiar `requirements.txt`, Cloud debe reconstruir el entorno.
- Usa el menú de administración de la app para **Reboot/Restart** si sigue sirviendo JS de una compilación anterior.
- Prueba en una ventana privada del navegador y, si funciona, limpia los datos/caché del sitio de Streamlit en la sesión habitual. Una recarga normal puede reutilizar módulos de JS antiguos.
- Verifica `Laboratorio`: al pulsar `Obtener recomendación` deben aparecer cuatro tarjetas legibles, barra de índice, explicación, hechos derivados, traza y exportación JSON.
- Verifica `Comparador`, `Sensibilidad` y `Base de conocimiento` tras abrir cada pestaña. Las funciones que dependen de Render deben mostrar un error controlado cuando la API está caída, sin tumbar el resto de la pantalla.
- En Chrome DevTools > Network, filtra por `.js` y consulta el código HTTP del recurso fallido; revisa también Console. Si la interfaz sigue sin cargar ni siquiera el encabezado, verifica el estado del hosting, conexión de Streamlit y logs de build: no se puede reparar una caída de infraestructura solamente cambiando un widget Python.

## Comprobaciones implementadas

La CI ejecuta `ruff check app demo scripts tests` y `pytest -q`, con `tests/test_streamlit_cloud_regressions.py` para validar:

- HTML de tarjetas, ausencia de `st.metric`, escape de etiquetas y tamaños de texto.
- Formato de los resultados de inferencia tras ejecutar `render_recommendation` con `AppTest`.
- Render básico de las cuatro pestañas sin hacer peticiones a la API.
- Entradas malformadas sin excepciones de Python, y respuestas de API inválidas con errores controlados.
- Protección de URL, redirecciones y cabeceras de autenticación.

**Limitación importante:** `streamlit.testing.v1.AppTest` ejecuta el código de Streamlit en Python, pero no valida la descarga de recursos JavaScript, websockets, caché de navegador o disponibilidad de Streamlit Cloud. Esas comprobaciones requieren una visita real a la aplicación publicada. Tampoco se ha alterado la lógica del motor, las ocho reglas ni `develop` de Laravel.
