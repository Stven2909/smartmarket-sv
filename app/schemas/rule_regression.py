"""Comparación no destructiva de dos bases de reglas sobre los mismos hechos."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.expert_system.models import KnowledgeBase, ProductionRule
from app.expert_system.rule_auditor import NUMERIC_FACTS
from app.schemas.recommendation import RecommendationRequest


class RuleSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    etiqueta: str = Field(min_length=1, max_length=80)
    reglas: list[ProductionRule] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def check_rules(self) -> "RuleSnapshot":
        KnowledgeBase(rules=self.reglas)
        numeric = sorted(
            {
                name
                for rule in self.reglas
                for name in rule.conditions
                if name in NUMERIC_FACTS
            }
        )
        if numeric:
            raise ValueError(
                "No se permiten comparaciones booleanas con hechos numéricos: "
                + ", ".join(numeric)
            )
        return self


class RegressionScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=100)
    hechos: RecommendationRequest


class RuleRegressionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anterior: RuleSnapshot
    propuesta: RuleSnapshot
    escenarios: list[RegressionScenario] = Field(min_length=1, max_length=10)


class RuleChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regla: str
    tipo: Literal["AGREGADA", "RETIRADA", "MODIFICADA"]
    campos: list[str]


class ScenarioRegression(BaseModel):
    model_config = ConfigDict(extra="forbid")

    escenario: str
    alternativa_id: str
    nivel_anterior: str
    nivel_propuesto: str
    regla_anterior: str | None
    regla_propuesta: str | None
    reglas_activas_anteriores: list[str]
    reglas_activas_propuestas: list[str]
    explicacion_anterior: str
    explicacion_propuesta: str
    indice_anterior: float
    indice_propuesto: float
    cambio_nivel: bool
    cambio_regla: bool
    cambio_activaciones: bool
    cambio_explicacion: bool
    regresion_critica: bool


class RuleRegressionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_anterior: str
    version_propuesta: str
    huella_anterior: str
    huella_propuesta: str
    reglas_agregadas: int = Field(ge=0)
    reglas_retiradas: int = Field(ge=0)
    reglas_modificadas: int = Field(ge=0)
    cambios_reglas: list[RuleChange]
    escenarios_evaluados: int = Field(ge=1)
    cambios_nivel: int = Field(ge=0)
    cambios_regla_ganadora: int = Field(ge=0)
    cambios_activaciones: int = Field(ge=0)
    cambios_explicacion: int = Field(ge=0)
    regresiones_criticas: int = Field(ge=0)
    resultados: list[ScenarioRegression]
    advertencias: list[str]
