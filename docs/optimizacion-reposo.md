# Optimización de arranque y consumo en reposo

SmartMarket SV usa dos procesos independientes: FastAPI en Render y la interfaz Streamlit Community Cloud. **El código no puede anular el reposo impuesto por el alojamiento gratuito.** El objetivo de esta optimización es gastar menos recursos en cada proceso y recuperar la funcionalidad tras un arranque en frío, sin peticiones artificiales.

## Streamlit: instalar solo lo necesario

El archivo `demo/requirements.txt` instala únicamente `streamlit` y `requests`. Community Cloud busca primero las dependencias junto al archivo de entrada `demo/streamlit_app.py`, antes de buscar las del directorio raíz. En consecuencia, no necesita instalar FastAPI, Uvicorn, ReportLab, Pydantic, Pytest ni pypdf para representar el laboratorio.

Se requiere Streamlit **1.55 o superior**, porque las pestañas ahora usan `st.tabs(..., on_change="rerun")`: solo la pestaña seleccionada construye sus controles, gráficas y tablas. Cambiar de pestaña produce una nueva ejecución; las otras tres permanecen sin evaluar. Las consultas HTTP siguen requiriendo acciones explícitas del usuario. La lectura de los nueve escenarios precargados usa `st.cache_data` con un límite de cuatro entradas.

Esto reduce trabajo en las interacciones y el conjunto de dependencias de la app, pero no mantiene un proceso activo si Community Cloud decide hibernarlo.

## Render: imports y cálculos diferidos

`requirements.txt` contiene solo las dependencias del servicio FastAPI: `fastapi`, `uvicorn`, `pydantic` y `reportlab` para el endpoint opcional PDF. La suite de pruebas y el cliente Streamlit se instalan desde `requirements-dev.txt` cuando se desarrolla o ejecuta CI.

El endpoint PDF importa `reportlab` únicamente **cuando se solicita generar un informe**. Importar `app.main` para atender `/health` o `/recommend` no carga el motor PDF.

Las reglas estáticas de producción se leen y validan una vez en el primer uso; las llamadas reciben copias independientes para evitar que un consumidor modifique la caché. Los archivos externos usados por los tests y la comparación de versiones siempre se leen sin utilizar esa caché. La auditoría de 2430 casos se calcula una vez por proceso cuando se llama por primera vez; después se sirven copias de un resultado cacheado.

Las cachés están **acotadas a una entrada** para los datos de producción y se liberan cuando el proceso se apaga o se despliega una nueva versión. No existe tarea de monitoreo, temporizador ni loop de ping.

## Despertar sin sondeos

Streamlit espera hasta 90 segundos una respuesta HTTP iniciada por el usuario. Este tiempo es un **límite de espera**, no trabajo adicional de CPU ni sondeos repetidos. Permite que Render termine su arranque en frío antes de declarar un timeout en condiciones normales.

En el alojamiento gratuito, el proveedor puede pausar el proceso cuando se queda sin tráfico. El código no impide ese apagado, ni cambia las reglas del proveedor.

## Medición y validación

```bash
python -m pip install -r requirements-dev.txt ruff
ruff check app demo scripts tests
pytest -q
pytest -q tests/test_idle_efficiency.py
```

Las pruebas verifican que: importar la API no cargue ReportLab, las cachés no filtren mutaciones, las dependencias estén separadas, y solo se rendericen los controles de la pestaña abierta. El resto de la suite verifica que las recomendaciones, las reglas, el comparador, el chatbot y la descarga PDF continúen funcionando.

No se incluye aquí un supuesto ahorro porcentual de RAM, CPU o segundos: para medirlo es necesario acceder a métricas reales del proceso en Render y Streamlit durante un periodo comparable.

## Operación

- En Render el build command permanece `pip install -r requirements.txt`, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- En Streamlit Community Cloud el entrypoint continúa siendo `demo/streamlit_app.py`; la plataforma detecta `demo/requirements.txt`.
- No configurar monitoreo artificial de `/health` para evitar el reposo: generaría tráfico y consumo continuo, contrario al objetivo.
- Si se requiere disponibilidad inmediata las 24 horas, se necesita alojamiento sin suspensión automática; el software no puede garantizarlo por sí solo.
