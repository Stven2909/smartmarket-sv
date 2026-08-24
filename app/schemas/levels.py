from typing import Final, Literal

RecommendationLevel = Literal["EXCELENTE", "BUENA", "NO_RECOMENDABLE"]

RECOMMENDATION_LEVELS: Final = frozenset({"EXCELENTE", "BUENA", "NO_RECOMENDABLE"})
