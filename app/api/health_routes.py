from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health", summary="Verifica la disponibilidad del servicio")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "smartmarket-expert-service"}
