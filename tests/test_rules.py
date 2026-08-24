import json

import pytest

from app.expert_system.models import DERIVED_FACT_NAMES
from app.expert_system.rule_loader import RuleLoaderError, load_rules


def test_rules_json_contains_rules():
    rules = load_rules()

    assert rules
    assert len(rules) == 8


def test_rule_ids_are_unique():
    rules = load_rules()

    assert len({rule.id for rule in rules}) == len(rules)


def test_priorities_are_positive_integers():
    rules = load_rules()

    assert all(isinstance(rule.priority, int) and rule.priority > 0 for rule in rules)


def test_recommendation_levels_are_valid():
    rules = load_rules()
    valid_levels = {"EXCELENTE", "BUENA", "NO_RECOMENDABLE"}

    assert all(rule.result.level in valid_levels for rule in rules)


def test_conditions_use_existing_derived_facts():
    rules = load_rules()

    assert all(set(rule.conditions).issubset(DERIVED_FACT_NAMES) for rule in rules)


@pytest.mark.parametrize("rule_id", ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08"])
def test_expected_rule_exists(rule_id):
    rules = load_rules()

    assert rule_id in {rule.id for rule in rules}


def test_r06_contains_five_expected_conditions():
    rule = next(rule for rule in load_rules() if rule.id == "R06")

    assert set(rule.conditions) == {
        "dentro_presupuesto",
        "todos_esenciales_disponibles",
        "distancia_cercana",
        "tiempo_bajo",
        "una_parada",
    }


def test_invalid_structure_raises_clear_error(tmp_path):
    invalid_path = tmp_path / "invalid-rules.json"
    invalid_path.write_text(
        json.dumps(
            [
                {
                    "id": "RXX",
                    "name": "Regla inválida",
                    "priority": 0,
                    "category": "PRUEBA",
                    "conditions": {},
                    "result": {
                        "level": "DESCONOCIDO",
                        "action": "",
                        "explanation": "",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuleLoaderError, match="Estructura inválida"):
        load_rules(invalid_path)


def test_duplicate_rule_ids_raise_clear_error(tmp_path):
    duplicate_path = tmp_path / "duplicate-rules.json"
    rules = [rule.model_dump() for rule in load_rules()]
    rules[1]["id"] = rules[0]["id"]
    duplicate_path.write_text(json.dumps(rules), encoding="utf-8")

    with pytest.raises(RuleLoaderError, match="IDs de reglas duplicados"):
        load_rules(duplicate_path)


def test_unknown_condition_fact_raises_clear_error(tmp_path):
    unknown_fact_path = tmp_path / "unknown-fact-rules.json"
    rules = [rule.model_dump() for rule in load_rules()]
    rules[0]["conditions"] = {"hecho_inexistente": True}
    unknown_fact_path.write_text(json.dumps(rules), encoding="utf-8")

    with pytest.raises(RuleLoaderError, match="hechos desconocidos"):
        load_rules(unknown_fact_path)


def test_corrupt_json_raises_clear_error(tmp_path):
    invalid_path = tmp_path / "corrupt-rules.json"
    invalid_path.write_text("{no es json", encoding="utf-8")

    with pytest.raises(RuleLoaderError, match="JSON corrupto"):
        load_rules(invalid_path)
