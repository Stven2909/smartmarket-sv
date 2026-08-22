from app.chatbot.intent_detector import detect_intent_details
from app.chatbot.response_templates import build_response
from app.schemas.chatbot import ChatRequest, ChatResponse


def chat(request: ChatRequest) -> ChatResponse:
    """Responde una pregunta usando solo el contexto recibido en la solicitud."""

    intent, supported = detect_intent_details(request.message)
    return ChatResponse(
        request_id=request.recommendation.request_id,
        intent=intent,
        response=build_response(
            intent,
            request.facts,
            request.recommendation,
        ),
        supported=supported,
    )
