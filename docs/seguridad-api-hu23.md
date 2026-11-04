# HU-23 — Seguridad del canal Laravel → Python (sin tocar develop)

## Límite de responsabilidades

El **backend Laravel** autentica a cada usuario final y valida que puede acceder a su lista de compra. **El servicio experto Python** solo autentica al servidor que lo consume mediante una clave compartida en la cabecera HTTP `X-API-Key`, valida 14 hechos y devuelve su inferencia. Un secreto de servidor **no sustituye** el inicio de sesión, los permisos por usuario ni los controles de Laravel.

No enviar la clave a React, a Streamlit en el navegador ni a los usuarios. Tampoco insertar el secreto en enlaces, parámetros de consulta, código fuente, fixtures, logs, archivos de ejemplo o repositorios. Toda comunicación de producción debe usar HTTPS.

## Configuración por ambiente

| Variable en Python (Render) | Función |
|---|---|
| `SMARTMARKET_ENV` | `production`, `prod`, `staging` y cualquier valor explícito desconocido exigen clave; vacío, `local`, `dev`, `development`, `test`, `testing` permiten desarrollo sin clave |
| `SMARTMARKET_API_KEY` | Secreto **principal** requerido para todos los endpoints `/api/v1/*` en ambientes desplegados |
| `SMARTMARKET_API_KEY_PREVIOUS` | Secreto anterior opcional, aceptado temporalmente durante una rotación y **nunca** válido si falta la clave principal |

Laravel debe guardar el mismo secreto como `EXPERT_SYSTEM_API_KEY` en su entorno de servidor y enviarlo por cabecera:

```http
POST /api/v1/recommend HTTP/1.1
Content-Type: application/json
X-API-Key: <secreto del backend, no del usuario>
```

En producción el resultado es:

- `200`: clave correcta y payload válido;
- `401`: clave ausente o incorrecta (no revela valores);
- `422`: clave aceptada pero hechos inconsistentes;
- `503`: entorno protegido sin clave principal configurada (fallo cerrado).

`/health` y `/ready` permanecen públicos para sondas operativas. En un proceso iniciado como productivo se deshabilitan `/docs`, `/redoc` y `/openapi.json`; esto **no reemplaza** la autenticación de las rutas.

**Importante para la integración:** el valor predeterminado de `SMARTMARKET_ENV` está vacío para no romper pruebas o demos locales existentes. Una instalación en Render que omita esta variable **y** la clave sigue en modo de desarrollo. Antes de anunciar que la API está protegida, configura `SMARTMARKET_ENV=production` y `SMARTMARKET_API_KEY` en el servicio Render y comprueba en vivo que falta de cabecera devuelve `401`. La detección de hosting por sí sola no activa esa protección para evitar un corte accidental durante el acuerdo con Laravel. Referencia: [variables de Render](https://render.com/docs/environment-variables) y [configuración de secretos](https://render.com/docs/configure-environment-variables).

## Cabeceras de respuesta

Cada solicitud a `/api/v1/*`, **incluidos los errores 401/422**, devuelve:

```http
Cache-Control: no-store
X-Content-Type-Options: nosniff
Vary: X-API-Key
```

Estas cabeceras desaconsejan el caché de recomendaciones y reducen ciertos riesgos del navegador; **no son un mecanismo de autorización**. La autenticación es exclusivamente la comprobación del secreto recibido.

## Rotación de clave sin interrumpir la comunicación

1. Crear una clave aleatoria nueva fuera del repositorio, y conservar la anterior solo durante la transición.
2. En el entorno de Python, establecer la nueva `SMARTMARKET_API_KEY` y el valor anterior en `SMARTMARKET_API_KEY_PREVIOUS`; desplegar el servicio.
3. Cambiar `EXPERT_SYSTEM_API_KEY` del backend Laravel por la nueva clave; comprobar que las solicitudes siguen en `200`.
4. Eliminar `SMARTMARKET_API_KEY_PREVIOUS` del entorno Python y desplegar de nuevo. La clave antigua debe devolver `401`.

El código nunca copia claves a los JSON. El soporte de rotación es opcional y temporal, no una segunda credencial permanente.

## Requisitos operativos de aceptación

- Probar en entorno de integración que todos los endpoints de negocio bloquean peticiones anónimas.
- Validar que el backend Laravel gestiona permisos de usuarios y nunca transmite la clave al navegador React.
- Confirmar que `/health` y `/ready` no exigen clave y que los endpoints de inferencia sí.
- Verificar los errores y las cabeceras con `tests/test_api_security_boundaries.py`.
- Confirmar que el despliegue público de Streamlit es una **demo independiente**. Si se desea restringirla a usuarios concretos, se necesita un control de acceso de Streamlit/plataforma aparte: la cabecera `X-API-Key` no protege por sí sola la página Streamlit.

**Fuera del alcance:** cuentas de usuario, contraseñas de Laravel, Sanctum, sesiones, control de acceso a listas, cambios en React y edición de `develop`. Nuestra API no conoce la identidad de los usuarios finales y no debe fingir conocerla.
