from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.recommendation import RecommendationResponse


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


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)
    facts: dict[str, Any] = Field(default_factory=dict)
    recommendation: RecommendationResponse


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    intent: ChatIntent
    response: str = Field(min_length=1)
    supported: bool
