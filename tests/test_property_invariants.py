"""HU-16: ensayos basados en propiedades y relaciones metamórficas."""

from hypothesis import HealthCheck, given, settings, strategies as st

from app.expert_system.classifiers import derive_facts
from app.expert_system.convenience_index import CRITICAL_RULE_IDS
from app.expert_system.inference_engine import run_inference_with_rules
from app.expert_system.rule_loader import load_rules
from app.schemas.recommendation import RecommendationRequest
from app.services.recommendation_service import recommend

CHECK = settings(
    max_examples=65,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


@st.composite
def alternatives(draw):
    essential_total = draw(st.integers(min_value=0, max_value=15))
    optional_total = draw(st.integers(min_value=1, max_value=15))
    essential = draw(st.integers(min_value=0, max_value=essential_total))
    optional = draw(st.integers(min_value=0, max_value=optional_total))
    budget = draw(st.integers(min_value=10, max_value=500))
    return RecommendationRequest(
        request_id="propiedades",
        alternativa_id="t-alternativa",
        costo_total=float(draw(st.integers(min_value=0, max_value=700))),
        presupuesto=float(budget),
        ahorro=float(draw(st.integers(min_value=0, max_value=80))),
        distancia_km=float(draw(st.integers(min_value=0, max_value=60))),
        distancia_adicional_km=float(draw(st.integers(min_value=0, max_value=50))),
        tiempo_estimado_min=float(draw(st.integers(min_value=0, max_value=200))),
        productos_disponibles=essential + optional,
        productos_totales=essential_total + optional_total,
        productos_esenciales_disponibles=essential,
        productos_esenciales_totales=essential_total,
        numero_supermercados=draw(st.integers(min_value=1, max_value=5)),
        promociones_aplicables=draw(st.booleans()),
    )


@CHECK
@given(alternatives())
def test_same_facts_always_produce_identical_explanations_and_trace(item):
    a = recommend(item).model_dump()
    b = recommend(item).model_dump()
    assert a == b
    assert len(a["trace"]) == 8
    assert 0 <= a["indice_conveniencia"] <= 100


@CHECK
@given(alternatives())
def test_every_derived_state_is_exclusive_and_consistent(item):
    facts = derive_facts(item)
    for partition in (
        ("dentro_presupuesto", "presupuesto_ligeramente_excedido",
         "presupuesto_muy_excedido"),
        ("todos_productos_disponibles", "faltan_productos"),
        ("todos_esenciales_disponibles", "faltan_esenciales"),
        ("ahorro_bajo", "ahorro_medio", "ahorro_alto"),
        ("distancia_cercana", "distancia_media", "distancia_lejana"),
        ("tiempo_bajo", "tiempo_medio", "tiempo_alto"),
        ("una_parada", "dos_paradas", "compra_fragmentada"),
    ):
        assert sum(facts[key] is True for key in partition) == 1
    if facts["todos_productos_disponibles"]:
        assert facts["todos_esenciales_disponibles"]
    if facts["faltan_esenciales"]:
        assert facts["faltan_productos"]


@CHECK
@given(alternatives())
def test_critical_activation_never_yields_a_favorable_decision(item):
    result = recommend(item)
    if CRITICAL_RULE_IDS.intersection(result.reglas_activadas):
        assert result.nivel_recomendacion == "NO_RECOMENDABLE"
        assert result.winning_rule in CRITICAL_RULE_IDS


@CHECK
@given(alternatives())
def test_rule_order_does_not_affect_winner_or_decision(item):
    rules = load_rules()
    normal = run_inference_with_rules(item, rules)
    reverse = run_inference_with_rules(item, list(reversed(rules)))
    assert normal["winning_rule"] == reverse["winning_rule"]
    assert normal["level"] == reverse["level"]


@CHECK
@given(alternatives())
def test_increasing_cost_beyond_critical_threshold_activates_r01(item):
    more_expensive = item.model_copy(
        update={"costo_total": item.presupuesto * 1.2}
    )
    recommendation = recommend(more_expensive)
    assert recommendation.winning_rule == "R01"
    assert recommendation.nivel_recomendacion == "NO_RECOMENDABLE"


@CHECK
@given(alternatives())
def test_losing_an_essential_item_activates_r02_without_budget_blocker(item):
    if item.productos_esenciales_totales == 0:
        return
    lost = item.model_copy(
        update={
            "costo_total": item.presupuesto,
            "productos_esenciales_disponibles": 0,
            "productos_disponibles": (
                item.productos_disponibles - item.productos_esenciales_disponibles
            ),
        }
    )
    if lost.productos_esenciales_totales > 0:
        outcome = recommend(lost)
        assert outcome.winning_rule == "R02"
        assert outcome.nivel_recomendacion == "NO_RECOMENDABLE"


@CHECK
@given(alternatives())
def test_index_does_not_improve_when_only_distance_increases(item):
    before = recommend(item)
    changed = item.model_copy(
        update={"distancia_adicional_km": item.distancia_adicional_km + 3}
    )
    after = recommend(changed)
    assert after.indice_conveniencia <= before.indice_conveniencia


@CHECK
@given(alternatives())
def test_index_cannot_decrease_if_only_saving_increases(item):
    before = recommend(item)
    changed = item.model_copy(update={"ahorro": item.ahorro + 7})
    after = recommend(changed)
    assert after.indice_conveniencia >= before.indice_conveniencia


@CHECK
@given(alternatives())
def test_adding_a_promotion_never_reduces_auxiliary_index(item):
    no_promo = item.model_copy(update={"promociones_aplicables": False})
    with_promo = item.model_copy(update={"promociones_aplicables": True})
    assert (
        recommend(with_promo).indice_conveniencia
        >= recommend(no_promo).indice_conveniencia
    )


@CHECK
@given(alternatives())
def test_json_round_trip_keeps_expert_decision_unchanged(item):
    serialized = item.model_dump_json()
    restored = RecommendationRequest.model_validate_json(serialized)
    assert recommend(item).model_dump() == recommend(restored).model_dump()
