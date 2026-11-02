"""Contrato independiente para comparar alternativas sin alterar /recommend."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.recommendation import RecommendationRequest, RecommendationResponse


class ComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alternativas: list[RecommendationRequest] = Field(min_length=2, max_length=10)

    @model_validator(mode="after")
    def validate_comparable_alternatives(self) -> "ComparisonRequest":
        identifiers = [option.alternativa_id for option in self.alternativas]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Cada alternativa debe tener un alternativa_id diferente")

        budgets = {option.presupuesto for option in self.alternativas}
        if len(budgets) != 1:
            raise ValueError("Las alternativas deben compartir el mismo presupuesto")
        return self


class RankedAlternative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    posicion: int = Field(ge=1)
    alternativa_id: str
    costo_total: float = Field(ge=0)
    riesgo_critico: bool
    motivo_posicion: str
    recomendacion: RecommendationResponse


class ComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mejor_alternativa_id: str
    criterio_orden: str
    ranking: list[RankedAlternative] = Field(min_length=2)
    advertencias: list[str]
