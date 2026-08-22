import json
from pathlib import Path

from pydantic import ValidationError

from app.expert_system.models import KnowledgeBase, ProductionRule


DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "rules.json"
)


class RuleLoaderError(ValueError):
    """Error legible al cargar o validar la base de conocimiento."""


def load_rules(path: Path | None = None) -> list[ProductionRule]:
    """Carga y valida rules.json desde una ruta absoluta o la ruta predeterminada."""

    rules_path = Path(path) if path is not None else DEFAULT_RULES_PATH

    try:
        raw_data = json.loads(rules_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuleLoaderError(
            f"No se encontró la base de conocimiento: {rules_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuleLoaderError(
            f"JSON corrupto en {rules_path}: línea {exc.lineno}, "
            f"columna {exc.colno}"
        ) from exc
    except OSError as exc:
        raise RuleLoaderError(
            f"No se pudo leer la base de conocimiento {rules_path}: {exc}"
        ) from exc

    if not isinstance(raw_data, list):
        raise RuleLoaderError(
            f"La base de conocimiento debe contener una lista de reglas: {rules_path}"
        )

    try:
        knowledge_base = KnowledgeBase.model_validate({"rules": raw_data})
    except ValidationError as exc:
        raise RuleLoaderError(
            f"Estructura inválida en la base de conocimiento {rules_path}: {exc}"
        ) from exc

    return knowledge_base.rules
