from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.levels import RecommendationLevel
from app.schemas.versions import CONTRACT_VERSION, RULES_VERSION

RECOMMENDATION_REQUEST_EXAMPLE = {
    "request_id": "demo-001",
    "alternativa_id": "supermercado-1",
    "costo_total": 42.50,
    "presupuesto": 50.00,
    "ahorro": 11.25,
    "distancia_km": 2.3,
    "distancia_adicional_km": 0.8,
    "tiempo_estimado_min": 12,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": True,
}

RECOMMENDATION_RESPONSE_EXAMPLE = {
    "request_id": "demo-001",
    "nivel_recomendacion": "EXCELENTE",
    "accion_sugerida": "Comprar todo en esta alternativa.",
    "explicacion": "Cumple el presupuesto y las condiciones principales.",
    "reglas_activadas": ["R06", "R07"],
    "prioridad_aplicada": "CONVENIENCIA",
    "hechos_derivados": {
        "dentro_presupuesto": True,
        "todos_esenciales_disponibles": True,
        "ahorro_alto": True,
        "porcentaje_productos_disponibles": 100.0,
    },
    "version_reglas": RULES_VERSION,
    "version_contrato": CONTRACT_VERSION,
    "winning_rule": "R06",
    "losing_rules": ["R07"],
    "trace": [
        {
            "rule_id": "R06",
            "evaluated": True,
            "activated": True,
            "conditions": {
                "dentro_presupuesto": {
                    "expected": True,
                    "actual": True,
                    "matched": True,
                }
            },
            "matched_conditions": ["dentro_presupuesto"],
            "unmatched_conditions": [],
            "reason": "Todas las condiciones se cumplieron.",
        }
    ],
    "indice_conveniencia": 82.39,
    "clasificacion_conveniencia": "ALTA_CONVENIENCIA",
    "componentes_conveniencia": {
        "ahorro": 0.5625,
        "disponibilidad": 1.0,
        "distancia": 0.96,
        "tiempo": 0.9,
        "promociones": 1.0,
    },
    "pesos_conveniencia": {
        "ahorro": 0.35,
        "disponibilidad": 0.25,
        "distancia": 0.2,
        "tiempo": 0.15,
        "promociones": 0.05,
    },
}

RECOMMENDATION_CRITICAL_RESPONSE_EXAMPLE = {
    **RECOMMENDATION_RESPONSE_EXAMPLE,
    "nivel_recomendacion": "NO_RECOMENDABLE",
    "accion_sugerida": "Replantear la lista o buscar productos sustitutos.",
    "explicacion": (
        "El costo supera el presupuesto en más de un 10%. "
        "La decisión principal fue determinada por la regla R01. "
        "El índice de conveniencia se muestra como información complementaria."
    ),
    "reglas_activadas": ["R01"],
    "prioridad_aplicada": "PRESUPUESTO",
    "hechos_derivados": {
        "dentro_presupuesto": False,
        "presupuesto_muy_excedido": True,
        "ahorro_alto": True,
        "porcentaje_productos_disponibles": 100.0,
    },
    "winning_rule": "R01",
    "losing_rules": [],
    "trace": [
        {
            "rule_id": "R01",
            "evaluated": True,
            "activated": True,
            "conditions": {
                "presupuesto_muy_excedido": {
                    "expected": True,
                    "actual": True,
                    "matched": True,
                }
            },
            "matched_conditions": ["presupuesto_muy_excedido"],
            "unmatched_conditions": [],
            "reason": "Todas las condiciones se cumplieron.",
        }
    ],
}


class RecommendationRequest(BaseModel):
    """Hechos de una alternativa de compra recibidos por el sistema experto."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [RECOMMENDATION_REQUEST_EXAMPLE]},
    )

    request_id: str = Field(min_length=1)
    alternativa_id: str = Field(min_length=1)
    costo_total: float = Field(ge=0)
    presupuesto: float = Field(gt=0)
    ahorro: float = Field(ge=0)
    distancia_km: float = Field(ge=0)
    distancia_adicional_km: float = Field(ge=0)
    tiempo_estimado_min: float = Field(ge=0)
    productos_disponibles: int = Field(ge=0)
    productos_totales: int = Field(gt=0)
    productos_esenciales_disponibles: int = Field(ge=0)
    productos_esenciales_totales: int = Field(gt=0)
    numero_supermercados: int = Field(ge=1)
    promociones_aplicables: bool

    @field_validator("request_id", "alternativa_id")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("no puede estar vacío ni contener solo espacios")
        return value

    @model_validator(mode="after")
    def validate_product_counts(self) -> "RecommendationRequest":
        if self.productos_disponibles > self.productos_totales:
            raise ValueError("productos_disponibles no puede superar productos_totales")

        if self.productos_esenciales_disponibles > self.productos_esenciales_totales:
            raise ValueError(
                "productos_esenciales_disponibles no puede superar productos_esenciales_totales"
            )

        return self


class RecommendationResponse(BaseModel):
    """Resultado explicable que devolverá el sistema experto."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [RECOMMENDATION_RESPONSE_EXAMPLE]},
    )

    request_id: str = Field(min_length=1)
    nivel_recomendacion: RecommendationLevel
    accion_sugerida: str = Field(min_length=1)
    explicacion: str = Field(min_length=1)
    reglas_activadas: list[str]
    prioridad_aplicada: str = Field(min_length=1)
    hechos_derivados: dict[str, bool | float]
    version_reglas: str = Field(min_length=1)
    winning_rule: str | None = None
    losing_rules: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    version_contrato: str = Field(default=CONTRACT_VERSION, min_length=1)
    indice_conveniencia: float | None = Field(default=None, ge=0, le=100)
    clasificacion_conveniencia: str | None = None
    componentes_conveniencia: dict[str, float] | None = None
    pesos_conveniencia: dict[str, float] | None = None
