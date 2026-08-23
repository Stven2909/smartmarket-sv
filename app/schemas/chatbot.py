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
    "AYUDA",
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
        "La recomendación actual es EXCELENTE porque cumple el presupuesto "
        "y las condiciones principales."
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
    recommendation: RecommendationResponse


class ChatResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [CHAT_RESPONSE_EXAMPLE]},
    )

    request_id: str = Field(min_length=1)
    intent: ChatIntent
    response: str = Field(min_length=1)
    supported: bool
