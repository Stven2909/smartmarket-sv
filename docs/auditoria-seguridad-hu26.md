# HU-26 — Auditoría y endurecimiento del servidor Python

**Fecha:** 3 de noviembre de 2026 (El Salvador). **Alcance:** servicio FastAPI en Render, cliente Streamlit Cloud, dependencias de Python y CI de nuestro fork. No modifica Laravel, React ni `develop`.

## Estado y niveles de evidencia

- **Código confirmado:** se examinaron los middleware, validación de `X-API-Key`, enrutamiento, cliente HTTP de Streamlit y los límites de los esquemas.
- **Pruebas reproducibles:** `tests/test_security_hardening_hu26.py` y `tests/test_security_external_probe.py` comprueban la autenticación, los límites de tamaño y el comportamiento de un verificador externo sin claves.
- **Dependencias:** `.github/workflows/python-security-audit.yml` ejecuta `pip-audit` sobre las dependencias instaladas para FastAPI y Streamlit. Las alertas del auditor representan vulnerabilidades reportadas, no pruebas de explotación.
- **Verificación del hosting:** esta revisión NO implica que se hayan ejecutado escáneres intrusivos ni pruebas de carga en Render. El entorno de auditoría no consiguió conectarse directamente a la URL pública de Render; las comprobaciones de producción siguen pendientes en una red que tenga acceso. No declarar el sitio libre de vulnerabilidades sin ese paso.

## Hallazgos y controles

| Riesgo | Observación | Mejora implementada |
|---|---|---|
| Alto — exposición accidental | `SMARTMARKET_ENV` podía omitirse en Render y permitir el modo de desarrollo si faltaba la clave | Se identifica automáticamente `RENDER=true` y se exige autenticación aunque `SMARTMARKET_ENV` esté vacío, mal escrito o configurado como desarrollo |
| Medio — una clave compartida | Laravel y Streamlit usaban el mismo secreto para llamar al motor | Variable adicional opcional `SMARTMARKET_API_KEY_STREAMLIT` con clave independiente y revocable. `SMARTMARKET_API_KEY` principal sigue siendo obligatorio |
| Medio — cuerpo HTTP sin límite central | Los esquemas Pydantic limitaban elementos, pero el servidor podía recibir un cuerpo JSON grande antes de validarlos | Un middleware ASGI rechaza con HTTP 413 los cuerpos mayores de 512 KiB, incluido envío por fragmentos sin `Content-Length` |
| Medio — vulnerabilidades de dependencias | Sin comprobación contra avisos de seguridad publicados en los workflows anteriores | Un nuevo trabajo de GitHub Actions ejecuta `pip-audit --local` en cada PR y fusión de `main` |
| Bajo — exposición en navegador | Los endpoints ya usaban `Cache-Control: no-store` y `X-Content-Type-Options: nosniff` | Se añaden `Referrer-Policy: no-referrer` y `X-Frame-Options: DENY` a las respuestas de `/api/v1/*` |
| Pendiente — abuso de recursos | Streamlit público permite al visitante solicitar inferencias usando la credencial del servidor | Evaluar un límite de peticiones por cliente/servicio y controles de acceso de la demo, sin castigar arbitrariamente a todas las personas bajo la misma IP compartida |
| Pendiente — entorno de producción | Render puede reiniciarse por inactividad y los logs/servicio están fuera del alcance de las pruebas de CI | Revisar despliegues, eventos, logs y métricas de Render desde el workspace correcto, sin usar fuerza bruta ni saturación |

## Claves separadas (opcional y compatible)

Render (nuestro motor):
```text
SMARTMARKET_ENV=production
SMARTMARKET_API_KEY=<CLAVE_PRIVADA_LARAVEL>
SMARTMARKET_API_KEY_STREAMLIT=<OTRA_CLAVE_PRIVADA_STREAMLIT>
```

Laravel (solo backend, nunca React):
```text
EXPERT_SYSTEM_API_KEY=<CLAVE_PRIVADA_LARAVEL>
```

Streamlit Community Cloud → aplicación → Settings → Secrets:
```toml
SMARTMARKET_API_URL = "https://sistema-experto-fork.onrender.com"
SMARTMARKET_API_KEY = "<OTRA_CLAVE_PRIVADA_STREAMLIT>"
```

El segundo secreto de Render es **opcional**. Si todavía no está configurado, Streamlit puede continuar enviando la clave principal como antes. Cuando decidas crear claves distintas, actualiza primero Render y después Streamlit; prueba «Verificar conexión» y por último revoca una clave secundaria obsoleta. No compartas las claves en chats ni en GitHub.

**Atención:** la clave de servicio confirma que la petición procede de un consumidor autorizado; no identifica usuarios finales. La aplicación Laravel es responsable de autenticar usuarios y aplicar sus permisos.

## Verificación pública no destructiva

Desde una terminal con salida a Internet, sin introducir ni enviar ninguna API key:

```bash
python -m scripts.security_probe --base-url https://sistema-experto-fork.onrender.com
```

El script hace **solo cuatro solicitudes GET** (sin bucles ni reintentos): `/health` debe devolver 200; `/api/v1/knowledge` debe devolver 401 sin clave; `/docs` y `/openapi.json` deben devolver 404. Una respuesta 200 en conocimiento u OpenAPI es motivo para revisar inmediatamente la configuración del servicio. 503 al consultar conocimiento también indica una configuración incorrecta o servicio no preparado. La prueba no busca CVEs en el sistema operativo ni acredita ausencia de vulnerabilidades.

## Limitaciones

- Los escáneres de dependencias verifican versiones efectivamente instaladas en CI, que podrían diferir de las que ejecuta una instancia de Render anterior. Revisar redeploy y dependencias instaladas en el servicio real.
- El límite de 512 KiB evita cargas grandes típicas, pero no es protección contra todo abuso de red o CPU; también conviene usar controles de infraestructura y proteger la demo pública.
- La huella SHA-256 de reglas identifica su contenido; no es una firma de autenticidad ni un sistema de autorización.
- No se realizaron pruebas de penetración disruptivas, escaneos masivos de puertos, denegación de servicio, solicitudes con claves robadas ni ataques al repositorio del compañero.
