"""Diagnóstico estructurado de consistencia de la base de reglas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FindingType = Literal[
    "ID_DUPLICADO",
    "CONDICIONES_DUPLICADAS",
    "SALIDAS_DIVERGENTES",
    "REGLA_SOMBREADA",
    "SIN_ACTIVACION_EN_MUESTRA",
]


class RuleFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: FindingType
    reglas: list[str] = Field(min_length=1)
    detalle: str


class RulePairOverlap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reglas: list[str] = Field(min_length=2, max_length=2)
    ganador_por_prioridad: str
    niveles: list[str] = Field(min_length=2, max_length=2)
    casos_coincidentes: int = Field(ge=1)
    ejemplo: dict[str, object]
    conflicto_de_nivel: bool
    resuelto_por_prioridad: bool = True


class RuleCoverageSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regla: str
    activaciones: int = Field(ge=0)


class RuleAuditResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_reglas: str
    reglas_evaluadas: int = Field(ge=1)
    escenarios_sinteticos: int = Field(ge=1)
    cobertura: list[RuleCoverageSample]
    hallazgos: list[RuleFinding]
    solapamientos: list[RulePairOverlap]
    resumen: str
    limitaciones: list[str]
