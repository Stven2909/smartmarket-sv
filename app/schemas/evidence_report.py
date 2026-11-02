"""Solicitud de un informe técnico PDF sobre escenarios suministrados."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.recommendation import RecommendationRequest


class EvidenceScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=100)
    hechos: RecommendationRequest


class EvidenceReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    escenarios: list[EvidenceScenario] = Field(min_length=2, max_length=10)

    @model_validator(mode="after")
    def check_comparability(self) -> "EvidenceReportRequest":
        identifiers = [item.hechos.alternativa_id for item in self.escenarios]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Cada alternativa debe tener un ID único.")
        if len({item.hechos.presupuesto for item in self.escenarios}) != 1:
            raise ValueError("Las alternativas deben compartir presupuesto.")
        return self
