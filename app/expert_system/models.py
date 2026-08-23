from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from app.schemas.levels import RecommendationLevel

DERIVED_FACT_NAMES = frozenset(
    {
        "dentro_presupuesto",
        "presupuesto_ligeramente_excedido",
        "presupuesto_muy_excedido",
        "todos_productos_disponibles",
        "faltan_productos",
        "todos_esenciales_disponibles",
        "faltan_esenciales",
        "ahorro_bajo",
        "ahorro_medio",
        "ahorro_alto",
        "distancia_cercana",
        "distancia_media",
        "distancia_lejana",
        "tiempo_bajo",
        "tiempo_medio",
        "tiempo_alto",
        "una_parada",
        "dos_paradas",
        "compra_fragmentada",
        "promociones_relevantes",
        "diferencia_presupuesto",
        "porcentaje_exceso_presupuesto",
        "porcentaje_productos_disponibles",
        "porcentaje_esenciales_disponibles",
    }
)


class RuleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: RecommendationLevel
    action: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class ProductionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    priority: StrictInt = Field(gt=0)
    category: str = Field(min_length=1)
    conditions: dict[str, StrictBool] = Field(min_length=1)
    result: RuleResult


class KnowledgeBase(BaseModel):
    """Conjunto de reglas y validaciones entre reglas."""

    rules: list[ProductionRule] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_rule_set(self) -> "KnowledgeBase":
        rule_ids = [rule.id for rule in self.rules]
        duplicated_ids = sorted(
            {rule_id for rule_id in rule_ids if rule_ids.count(rule_id) > 1}
        )
        if duplicated_ids:
            raise ValueError(
                f"IDs de reglas duplicados: {', '.join(duplicated_ids)}"
            )

        for rule in self.rules:
            unknown_facts = sorted(
                set(rule.conditions) - DERIVED_FACT_NAMES
            )
            if unknown_facts:
                raise ValueError(
                    f"La regla {rule.id} utiliza hechos desconocidos: "
                    f"{', '.join(unknown_facts)}"
                )

        return self
