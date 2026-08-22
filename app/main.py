from fastapi import FastAPI

from app.api.health_routes import router as health_router
from app.api.chatbot_routes import router as chatbot_router
from app.api.recommendation_routes import router as recommendation_router


app = FastAPI(
    title="SmartMarket SV Expert Service",
    version="0.1.0",
    description="API independiente para el Sistema Experto de SmartMarket SV.",
)

app.include_router(health_router)
app.include_router(recommendation_router)
app.include_router(chatbot_router)
