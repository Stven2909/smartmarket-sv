# HU-27 — Límite ligero de uso para la demo pública, sin perjudicar Laravel

## Motivo

La página de Streamlit Cloud puede ser pública. Aunque la clave del servidor no aparezca en JavaScript, una visita puede activar llamadas al servicio Python. En un plan gratuito es sensato limitar la carga accidental o automatizada sin mantener Render despierto mediante tareas de vigilancia.

## Funcionamiento

Cuando Render tiene una **clave secundaria diferente** en `SMARTMARKET_API_KEY_STREAMLIT`, las peticiones hechas con esa credencial se limitan a **60 solicitudes por minuto** de forma predeterminada, por proceso. Puedes ajustar el valor con `SMARTMARKET_STREAMLIT_RATE_LIMIT_PER_MINUTE`, entre 1 y 600; valores inválidos vuelven al límite seguro de 60.

No se utiliza la IP del visitante ni `X-Forwarded-For`: todas las visitas a una demo pública usan la misma credencial de servidor. La cuota, por tanto, se comparte entre todos los visitantes de esa demo. **Laravel no consume esa cuota** cuando utiliza `SMARTMARKET_API_KEY`, y la clave de rotación `SMARTMARKET_API_KEY_PREVIOUS` tampoco consume la cuota de Streamlit.

Cuando se agota la cuota, el servidor devuelve `429 Too Many Requests` con `Retry-After` en segundos y `Cache-Control: no-store`. Al finalizar la ventana de 60 segundos, el servicio acepta nuevas solicitudes automáticamente. No hay hilos, temporizadores, bases de datos ni peticiones en segundo plano; se usa una cola pequeña acotada y un candado por proceso.

**Si Streamlit todavía utiliza la misma clave principal que Laravel, no se aplica este límite**, para evitar interrumpir por sorpresa al backend del compañero. Se aplica únicamente después de asignarle un secreto distinto a Streamlit.

## Configuración sugerida

En el servicio de Render:

```text
SMARTMARKET_ENV=production
SMARTMARKET_API_KEY=<clave-Laravel>
SMARTMARKET_API_KEY_STREAMLIT=<clave-diferente-de-Streamlit>
SMARTMARKET_STREAMLIT_RATE_LIMIT_PER_MINUTE=60
```

En Streamlit Community Cloud → aplicación → Settings → Secrets:

```toml
SMARTMARKET_API_URL = "https://sistema-experto-fork.onrender.com"
SMARTMARKET_API_KEY = "<clave-diferente-de-Streamlit>"
```

En Laravel se conserva `EXPERT_SYSTEM_API_KEY=<clave-Laravel>`. La cuota de Streamlit no requiere modificar `develop`.

## Limitaciones y consideraciones

- Esta cuota es **por proceso de Python**, no distribuida. Varios workers podrían admitir solicitudes adicionales. No sustituye un WAF, una cuota en el proxy ni controles de acceso de Streamlit.
- Los visitantes de la demo comparten la cuota. Si hay muchos asistentes en una exposición, podría ser necesario aumentar el límite temporalmente con cuidado, o restringir el acceso a la demo.
- No limita a clientes anónimos que reciben HTTP 401; sí bloquea las inferencias protegidas antes de ejecutarlas cuando la cuota de Streamlit se agota. Render/CDN pueden disponer de sus propios límites de borde.
- Los controles de seguridad de la API siguen siendo necesarios: autenticación, tamaño máximo del cuerpo y supervisión del despliegue.
- No se imprime ni almacena el texto de ninguna credencial; la cuota solo guarda marcas de tiempo.

## Pruebas

`tests/test_streamlit_rate_limit.py` comprueba que la tercera solicitud con límite de 2 se rechaza con 429, que se informa `Retry-After`, que Laravel continúa recibiendo 200, que la cuota se recupera cuando transcurre la ventana, y que valores de configuración incorrectos nunca desactivan accidentalmente la protección.

La CI vuelve a analizar las dependencias con `pip-audit` y conserva los escenarios R01–R08, el contrato Laravel de entrada de 14 campos y respuesta de 16 campos.
