from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Verifica la disponibilidad del servicio",
    responses={
        200: {
            "description": "Servicio disponible.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "service": "smartmarket-expert-service",
                    }
                }
            },
        }
    },
)
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "smartmarket-expert-service"}
