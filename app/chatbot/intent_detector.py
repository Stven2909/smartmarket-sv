import unicodedata
from typing import Literal

Intent = Literal[
    "EXPLICACION",
    "PRESUPUESTO",
    "AHORRO",
    "DISTANCIA",
    "TIEMPO",
    "PRODUCTOS",
    "MEJORAR",
    "REGLAS",
    "INDICE",
    "REGLA_GANADORA",
    "REGLAS_PERDEDORAS",
    "AYUDA",
    "NO_DISPONIBLE",
]


# El orden es deliberado: REGLAS y otras intenciones específicas se detectan
# antes de EXPLICACION, que también puede contener "por que".
INTENT_KEYWORDS: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (
        "REGLAS_PERDEDORAS",
        (
            "reglas perdedoras",
            "reglas perdedor",
            "reglas perdieron",
            "losing_rules",
            "losing rules",
        ),
    ),
    (
        "REGLA_GANADORA",
        (
            "regla ganadora",
            "regla que gano",
            "que regla gano",
            "regla gano",
            "winning_rule",
            "winning rule",
        ),
    ),
    (
        "INDICE",
        (
            "indice de conveniencia",
            "indice auxiliar",
            "indice",
            "conveniencia",
        ),
    ),
    ("REGLAS", ("regla", "reglas", "criterio", "criterios", "decidio")),
    ("MEJORAR", ("mejorar", "cambiar", "deberia", "mejor recomendacion")),
    (
        "EXPLICACION",
        ("por que", "porque", "motivo", "razon", "recomienda", "recomendacion"),
    ),
    ("PRESUPUESTO", ("presupuesto", "alcanza", "queda", "excede", "exceso")),
    ("AHORRO", ("ahorro", "ahorrar", "vale la pena")),
    ("DISTANCIA", ("lejos", "kilometro", "kilometros", "distancia", "recorrer")),
    ("TIEMPO", ("tardare", "tiempo", "toma", "recorrido largo")),
    ("PRODUCTOS", ("producto", "productos", "disponible", "esencial", "faltan")),
    ("AYUDA", ("ayuda", "que puedes hacer", "como funciona")),
)


def normalize_text(message: str) -> str:
    """Pasa el mensaje a minúsculas y elimina acentos."""

    normalized = unicodedata.normalize("NFD", message.lower())
    return "".join(character for character in normalized if unicodedata.category(character) != "Mn")


def detect_intent_details(message: str) -> tuple[Intent, bool]:
    normalized_message = normalize_text(message)

    for intent, keywords in INTENT_KEYWORDS:
        if any(keyword in normalized_message for keyword in keywords):
            return intent, True

    return "AYUDA", False


def detect_intent(message: str) -> Intent:
    """Detecta una intención conocida o devuelve AYUDA si no reconoce el texto."""

    intent, _ = detect_intent_details(message)
    return intent
