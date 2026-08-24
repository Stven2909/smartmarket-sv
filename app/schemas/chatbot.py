from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.recommendation import (
    RECOMMENDATION_RESPONSE_EXAMPLE,
    RecommendationResponse,
)


ChatIntent = Literal[
    "EXPLICACION",
    "PRESUPUESTO",
    "AHORRO",
    "DISTANCIA",
    "TIEMPO",
    "PRODUCTOS",
    "MEJORAR",
    "REGLAS",
    "INDICE",
    "REGLA_GANADORA",
    "REGLAS_PERDEDORAS",
    "AYUDA",
    "NO_DISPONIBLE",
]


CHAT_REQUEST_EXAMPLE = {
    "message": "¿Por qué se recomienda esta alternativa?",
    "facts": {
        "costo_total": 42.5,
        "presupuesto": 50.0,
        "ahorro": 11.25,
        "distancia_adicional_km": 0.8,
        "tiempo_estimado_min": 12,
        "productos_disponibles": 10,
        "productos_totales": 10,
        "productos_esenciales_disponibles": 6,
        "productos_esenciales_totales": 6,
        "promociones_aplicables": True,
    },
    "recommendation": RECOMMENDATION_RESPONSE_EXAMPLE,
}

CHAT_RESPONSE_EXAMPLE = {
    "request_id": "demo-001",
    "intent": "EXPLICACION",
    "response": (
        "Te recomiendo esta opción porque la compra está dentro de tu "
        "presupuesto, incluye los productos esenciales y el recorrido adicional "
        "es corto."
    ),
    "supported": True,
}


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [CHAT_REQUEST_EXAMPLE]},
    )

    message: str = Field(min_length=1)
    facts: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = Field(default=None, min_length=1)
    recommendation: RecommendationResponse | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [CHAT_RESPONSE_EXAMPLE]},
    )

    request_id: str | None = None
    intent: ChatIntent
    response: str = Field(min_length=1)
    supported: bool
