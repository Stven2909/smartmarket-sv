"""Bounded API request bodies to protect a small free-tier service.

This runs before the request reaches FastAPI/Pydantic and never buffers more
than MAX_API_REQUEST_BYTES of accepted data. No dependency or background task.
"""

from starlette.responses import JSONResponse

MAX_API_REQUEST_BYTES = 512 * 1024
API_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


class RequestBodySizeLimitMiddleware:
    """Reject oversized HTTP bodies before FastAPI parses JSON or generates PDFs."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope.get("method", "").upper() not in API_BODY_METHODS
            or not scope.get("path", "").startswith("/api/v1/")
        ):
            await self.app(scope, receive, send)
            return

        async def reject(status_code: int, detail: str) -> None:
            response = JSONResponse(
                status_code=status_code,
                content={"detail": detail},
                headers={
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                    "Vary": "X-API-Key",
                },
            )
            await response(scope, receive, send)

        sizes = [
            value for name, value in scope.get("headers", ())
            if name.lower() == b"content-length"
        ]
        if len(sizes) > 1:
            await reject(400, "Encabezado Content-Length duplicado.")
            return
        if sizes:
            try:
                claimed = int(sizes[0])
            except (ValueError, OverflowError):
                await reject(400, "Content-Length no válido.")
                return
            if claimed < 0:
                await reject(400, "Content-Length no válido.")
                return
            if claimed > MAX_API_REQUEST_BYTES:
                await reject(413, "Cuerpo HTTP demasiado grande.")
                return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > MAX_API_REQUEST_BYTES:
                await reject(413, "Cuerpo HTTP demasiado grande.")
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        # Replay the bounded body once to the original ASGI application.
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
