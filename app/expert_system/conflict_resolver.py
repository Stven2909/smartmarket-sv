from app.expert_system.models import ProductionRule


def resolve_conflicts(
    activated_rules: list[ProductionRule],
) -> dict[str, object]:
    """Selecciona la regla de menor prioridad y desempata por ID ascendente."""

    ordered_rules = sorted(
        activated_rules,
        key=lambda rule: (rule.priority, rule.id),
    )
    winner = ordered_rules[0] if ordered_rules else None

    return {
        "winner": winner,
        "losers": ordered_rules[1:] if winner is not None else [],
    }
