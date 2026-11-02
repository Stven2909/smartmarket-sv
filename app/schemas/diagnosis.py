"""Contrato opcional para diagnosticar las condiciones de las reglas favorables."""

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.schemas.recommendation import RecommendationRequest


class DiagnosisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alternativa: RecommendationRequest


class MissingCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hecho: str
    valor_esperado: StrictBool
    valor_actual: StrictBool
    orientacion: str


class RuleOpportunity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regla: str
    nivel_posible: str
    prioridad: int = Field(gt=0)
    condiciones_cumplidas: int = Field(ge=0)
    condiciones_totales: int = Field(gt=0)
    activa: bool
    faltantes: list[MissingCondition]


class CriticalRisk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regla: str
    motivo: str


class DiagnosisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alternativa_id: str
    nivel_actual: str
    regla_ganadora: str | None
    riesgos_criticos: list[CriticalRisk]
    oportunidades: list[RuleOpportunity]
    resumen: str
    advertencias: list[str]
