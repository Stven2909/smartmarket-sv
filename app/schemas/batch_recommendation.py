"""Optional multi-alternative inference contract; not an economic optimizer."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.recommendation import RecommendationRequest, RecommendationResponse

MAX_BATCH_SIZE = 50


class BatchRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alternativas: list[RecommendationRequest] = Field(
        min_length=1,
        max_length=MAX_BATCH_SIZE,
        description="One independently evaluated Laravel fact set per alternative.",
    )

    @model_validator(mode="after")
    def validate_request_ids(self) -> "BatchRecommendationRequest":
        identifiers = [option.request_id for option in self.alternativas]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Cada alternativa necesita un request_id distinto")
        return self


class BatchRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resultados: list[RecommendationResponse] = Field(min_length=1)
