from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RecommendationLevel = Literal["EXCELENTE", "BUENA", "NO_RECOMENDABLE"]


class RecommendationRequest(BaseModel):
    """Hechos de una alternativa de compra recibidos por el sistema experto."""

    model_config = ConfigDict(extra="forbid")

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
            raise ValueError(
                "productos_disponibles no puede superar productos_totales"
            )

        if (
            self.productos_esenciales_disponibles
            > self.productos_esenciales_totales
        ):
            raise ValueError(
                "productos_esenciales_disponibles no puede superar "
                "productos_esenciales_totales"
            )

        return self


class RecommendationResponse(BaseModel):
    """Resultado explicable que devolverá el sistema experto."""

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
