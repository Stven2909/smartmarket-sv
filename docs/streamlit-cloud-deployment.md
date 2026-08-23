# Publicación de SmartMarket SV

## Qué se publica

SmartMarket SV tiene dos procesos separados:

```text
Compañeros
    |
    v
Streamlit Community Cloud
    |
    | HTTP/HTTPS
    v
FastAPI público
    |
    v
Motor de inferencia y chatbot
```

Streamlit publica la interfaz visual. No ejecuta automáticamente FastAPI ni
puede usar `127.0.0.1` para llegar al computador del desarrollador. Por eso
se necesitan dos URLs:

- **URL de la demo:** la asigna Streamlit, por ejemplo
  `https://smartmarket-demo.streamlit.app`.
- **URL de la API:** la asigna el proveedor donde se publique FastAPI, por
  ejemplo `https://smartmarket-api.onrender.com`.

Los compañeros únicamente necesitan abrir la URL de la demo. La aplicación
usa internamente la URL pública de FastAPI.

## Requisito del repositorio

El repositorio actual es público, pero Streamlit Community Cloud requiere
permisos de administrador sobre el repositorio para desplegar una aplicación.
Si el repositorio pertenece a otra persona, hay dos alternativas:

1. Crear un **fork** del repositorio en la cuenta personal que se usará en
   Streamlit Community Cloud.
2. Pedir al propietario que otorgue permisos de administrador y autorizar la
   aplicación de Streamlit para acceder al repositorio.

El fork es la opción más sencilla para una demo académica. No se deben
compartir contraseñas ni tokens.

## Publicar FastAPI

Streamlit Cloud no es el servidor de FastAPI. Primero hay que publicar el
servicio Python en un proveedor de servicios web que permita ejecutar un
proceso HTTP. Por ejemplo, en Render:

1. Crear una cuenta e iniciar un nuevo **Web Service**.
2. Seleccionar el fork de `smartmarket-sv`.
3. Usar la rama `expert-system-python`.
4. Usar estos comandos:

   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

5. Configurar el health check como `/health`.
6. Esperar el despliegue y copiar la URL HTTPS asignada.
7. Verificar que `https://TU-API/health` responda con HTTP 200.

El servicio no necesita PostgreSQL ni variables secretas para esta demo. Los
escenarios y reglas se cargan desde los archivos JSON del repositorio.

## Publicar Streamlit Community Cloud

1. Abrir `https://share.streamlit.io`.
2. Iniciar sesión con la cuenta de GitHub que tiene el fork o permisos de
   administrador.
3. Seleccionar **Create app**.
4. Elegir:

   - Repository: el fork personal de `smartmarket-sv`.
   - Branch: `expert-system-python`.
   - Main file path: `demo/streamlit_app.py`.

5. Elegir un subdominio, por ejemplo `smartmarket-sv-demo`, si está
   disponible.
6. Antes de abrir la aplicación, entrar a **Settings > Secrets** y agregar:

   ```toml
   SMARTMARKET_API_URL = "https://TU-API-FASTAPI.example.com"
   ```

7. Guardar y reiniciar la aplicación.

El archivo `demo/streamlit_app.py` busca la URL en este orden:

1. Variable de entorno `SMARTMARKET_API_URL`.
2. Secret de Streamlit `SMARTMARKET_API_URL`.
3. Valor local `http://127.0.0.1:8001`.

El tercer valor solo sirve para desarrollo local. No debe usarse en la nube.

## URL que se comparte con el grupo

Se comparte la URL de Streamlit, no la URL interna local de FastAPI:

```text
https://smartmarket-sv-demo.streamlit.app
```

Los compañeros no necesitan instalar Python, FastAPI, Streamlit ni Laravel.
Solo necesitan un navegador y acceso a Internet.

## Qué puede probar un compañero

La demo permite:

- Consultar el estado de FastAPI.
- Seleccionar escenarios simulados.
- Editar presupuesto, costo, ahorro, distancia, tiempo y disponibilidad.
- Solicitar una recomendación.
- Ver el `request_id`.
- Ver el nivel, la regla ganadora, las reglas activadas y la prioridad.
- Ver los hechos derivados y la versión de reglas.
- Preguntar al chatbot explicativo.

Los datos usados son simulados. La aplicación no consulta Laravel, no usa
PostgreSQL, no usa scraping y no utiliza IA generativa.

## Contrato entre Laravel y Python

Cuando el backend Laravel se integre, debe llamar a la URL de FastAPI, no a la
URL de Streamlit:

```text
POST https://TU-API-FASTAPI.example.com/api/v1/recommend
POST https://TU-API-FASTAPI.example.com/api/v1/chat
```

Laravel conserva el papel de orquestador y envía únicamente hechos validados.
Python deriva hechos internos, evalúa las reglas, resuelve conflictos y
devuelve la explicación. Laravel no debe enviar SQL, reglas ni modelos
internos.

## Errores frecuentes

### La aplicación no aparece en Streamlit

La cuenta de GitHub no tiene permisos de administrador sobre el repositorio.
Usar un fork personal o solicitar acceso al propietario.

### La demo abre, pero muestra error de conexión

Revisar que el Secret `SMARTMARKET_API_URL` contenga la URL HTTPS de FastAPI,
sin `/docs` y sin `/api/v1/recommend` al final. La aplicación agregará las
rutas automáticamente.

### FastAPI responde 422

El formulario contiene un valor inválido o inconsistente. Revisar los campos
mostrados por la interfaz y el contrato Pydantic.

### FastAPI responde 500 o está dormido

Revisar los logs del proveedor de FastAPI y probar primero `/health`. La demo
no ejecuta el motor localmente ni puede reparar un servicio API apagado.

## Desarrollo local

Terminal 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Terminal 2:

```powershell
.\.venv\Scripts\python.exe -m streamlit run demo/streamlit_app.py
```

Para apuntar explícitamente a otra API durante la sesión:

```powershell
$env:SMARTMARKET_API_URL = "https://TU-API-FASTAPI.example.com"
.\.venv\Scripts\python.exe -m streamlit run demo/streamlit_app.py
```
