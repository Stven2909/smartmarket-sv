from fastapi import APIRouter, HTTPException

from app.expert_system.inference_engine import InferenceError
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommendation_service import recommend


router = APIRouter(prefix="/api/v1", tags=["recommendations"])


@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    summary="Genera una recomendación explicable",
)
def create_recommendation(
    request: RecommendationRequest,
) -> RecommendationResponse:
    try:
        return recommend(request)
    except InferenceError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Error controlado del motor de inferencia: {exc}",
        ) from exc
