from fastapi import APIRouter

from app.chatbot.chatbot_service import chat
from app.schemas.chatbot import CHAT_RESPONSE_EXAMPLE, ChatRequest, ChatResponse


router = APIRouter(prefix="/api/v1", tags=["chatbot"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Explica una recomendación con un chatbot determinista",
    description=(
        "Responde usando únicamente los hechos y la recomendación recibidos; "
        "no ejecuta reglas nuevas ni genera datos inventados."
    ),
    responses={
        200: {
            "description": "Respuesta determinista del chatbot.",
            "content": {
                "application/json": {
                    "example": CHAT_RESPONSE_EXAMPLE,
                }
            },
        },
        422: {
            "description": "Solicitud de chatbot inválida.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "message"],
                                "msg": "String should have at least 1 character",
                                "type": "string_too_short",
                            }
                        ]
                    }
                }
            },
        },
    },
)
def create_chat_response(request: ChatRequest) -> ChatResponse:
    return chat(request)
