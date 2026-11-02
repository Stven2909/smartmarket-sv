"""Vista de solo lectura de las reglas y parámetros realmente usados."""

from pydantic import BaseModel, ConfigDict

from app.expert_system.models import ProductionRule


class KnowledgeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rules: list[ProductionRule]
    thresholds: dict[str, float]
    weights: dict[str, float]
    rules_version: str
    thresholds_version: str
    convenience_version: str
