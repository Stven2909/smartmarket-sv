from fastapi import APIRouter

from app.chatbot.chatbot_service import chat
from app.schemas.chatbot import ChatRequest, ChatResponse


router = APIRouter(prefix="/api/v1", tags=["chatbot"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Explica una recomendación con un chatbot determinista",
)
def create_chat_response(request: ChatRequest) -> ChatResponse:
    return chat(request)
