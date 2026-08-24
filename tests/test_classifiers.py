from app.expert_system.classifiers import derive_facts
from app.schemas.recommendation import RecommendationRequest

VALID_REQUEST = {
    "request_id": "demo-001",
    "alternativa_id": "supermercado-1",
    "costo_total": 42.50,
    "presupuesto": 50.00,
    "ahorro": 11.25,
    "distancia_km": 2.3,
    "distancia_adicional_km": 0.8,
    "tiempo_estimado_min": 12,
    "productos_disponibles": 10,
    "productos_totales": 10,
    "productos_esenciales_disponibles": 6,
    "productos_esenciales_totales": 6,
    "numero_supermercados": 1,
    "promociones_aplicables": True,
}


def make_request(**changes) -> RecommendationRequest:
    return RecommendationRequest.model_validate({**VALID_REQUEST, **changes})


def test_ideal_scenario_derives_expected_facts():
    facts = derive_facts(make_request())

    assert facts["dentro_presupuesto"] is True
    assert facts["presupuesto_ligeramente_excedido"] is False
    assert facts["presupuesto_muy_excedido"] is False
    assert facts["todos_productos_disponibles"] is True
    assert facts["faltan_productos"] is False
    assert facts["todos_esenciales_disponibles"] is True
    assert facts["faltan_esenciales"] is False
    assert facts["ahorro_alto"] is True
    assert facts["distancia_cercana"] is True
    assert facts["tiempo_bajo"] is True
    assert facts["una_parada"] is True
    assert facts["compra_fragmentada"] is False
    assert facts["promociones_relevantes"] is True


def test_derives_very_exceeded_budget():
    facts = derive_facts(make_request(costo_total=56, presupuesto=50))

    assert facts["dentro_presupuesto"] is False
    assert facts["presupuesto_ligeramente_excedido"] is False
    assert facts["presupuesto_muy_excedido"] is True
    assert facts["diferencia_presupuesto"] == -6
    assert facts["porcentaje_exceso_presupuesto"] == 12


def test_derives_missing_essential_products():
    facts = derive_facts(
        make_request(
            productos_esenciales_disponibles=5,
            productos_esenciales_totales=6,
        )
    )

    assert facts["todos_esenciales_disponibles"] is False
    assert facts["faltan_esenciales"] is True
    assert facts["porcentaje_esenciales_disponibles"] == (5 / 6 * 100)


def test_derives_far_distance_with_low_savings():
    facts = derive_facts(make_request(distancia_adicional_km=8, ahorro=2.99))

    assert facts["distancia_lejana"] is True
    assert facts["distancia_cercana"] is False
    assert facts["ahorro_bajo"] is True


def test_derives_high_travel_time():
    facts = derive_facts(make_request(tiempo_estimado_min=45))

    assert facts["tiempo_alto"] is True
    assert facts["tiempo_medio"] is False
    assert facts["tiempo_bajo"] is False


def test_derives_fragmented_purchase():
    facts = derive_facts(make_request(numero_supermercados=3))

    assert facts["compra_fragmentada"] is True
    assert facts["una_parada"] is False
    assert facts["dos_paradas"] is False


def test_derives_promotions():
    facts = derive_facts(make_request(promociones_aplicables=True))

    assert facts["promociones_relevantes"] is True
