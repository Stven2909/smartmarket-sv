"""Modelos del análisis hipotético, independientes del contrato de recomendación."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.recommendation import RecommendationRequest, RecommendationResponse


class SensitivityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alternativa: RecommendationRequest


class SensitivityCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    escenario: str
    descripcion: str
    cambios: dict[str, float | int | bool]
    recomendacion: RecommendationResponse
    cambia_decision: bool
    diferencia_indice: float


class SensitivityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alternativa_id: str
    escenario_base: RecommendationResponse
    escenarios: list[SensitivityCase] = Field(min_length=2)
    cantidad_decisiones_distintas: int = Field(ge=0)
    interpretacion: str
    advertencias: list[str]
