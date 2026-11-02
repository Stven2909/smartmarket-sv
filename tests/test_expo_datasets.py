"""Valida que los CSV de exposición sean íntegros y no falseen procedencia."""

import csv
from collections import Counter
from pathlib import Path

from app.schemas.comparison import ComparisonRequest
from app.schemas.recommendation import RecommendationRequest
from app.services.comparison_service import compare_alternatives
from demo.manual_dataset import import_dataset

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "data" / "escenarios_exposicion_300.csv"
CATALOG = ROOT / "data" / "precios_referencia_web_expo.csv"


def test_three_hundred_synthetic_alternatives_import_successfully():
    imported = import_dataset(SCENARIOS.read_bytes(), SCENARIOS.name)
    assert not imported.errors
    assert imported.total_rows == 300
    assert len(imported.scenarios) == 300
    assert len({item["facts"]["alternativa_id"] for item in imported.scenarios}) == 300
    assert all(item["metadata"]["procedencia"] == "sintetico" for item in imported.scenarios)
    assert all(item["metadata"]["fuente_url"].startswith("https://") for item in imported.scenarios)


def test_scenarios_are_grouped_into_fifteen_comparable_lists():
    imported = import_dataset(SCENARIOS.read_bytes(), SCENARIOS.name)
    counts = Counter(item["facts"]["request_id"] for item in imported.scenarios)
    assert len(counts) == 15
    assert set(counts.values()) == {20}
    for listing in counts:
        sample = [
            item["facts"]
            for item in imported.scenarios
            if item["facts"]["request_id"] == listing
        ]
        assert len({item["presupuesto"] for item in sample}) == 1
        assert len({item["productos_totales"] for item in sample}) == 1
        assert len({item["productos_esenciales_totales"] for item in sample}) == 1
        assert all(RecommendationRequest.model_validate(item) for item in sample)


def test_synthetic_comparison_does_not_depend_on_external_sources():
    imported = import_dataset(SCENARIOS.read_bytes(), SCENARIOS.name)
    group = [
        item["facts"]
        for item in imported.scenarios
        if item["facts"]["request_id"] == "expo-lista-01"
    ]
    report = compare_alternatives(
        ComparisonRequest(
            alternativas=[
                RecommendationRequest.model_validate(row)
                for row in group[:10]
            ]
        )
    )
    assert len(report.ranking) == 10
    assert all(len(option.recomendacion.trace) == 8 for option in report.ranking)


def test_web_catalog_is_explicitly_a_price_reference_not_real_inventory():
    with CATALOG.open("r", encoding="utf-8", newline="") as file:
        catalog = list(csv.DictReader(file))
    assert len(catalog) >= 60
    assert len({row["registro_id"] for row in catalog}) == len(catalog)
    assert all(row["moneda"] == "USD" for row in catalog)
    assert all(row["tipo_dato"] == "referencia_web_publica" for row in catalog)
    assert all(row["fecha_consulta"] == "2026-11-02" for row in catalog)
    assert all(row["fuente_url"].startswith("https://") for row in catalog)
    assert all(float(row["precio_mostrado_usd"]) > 0 for row in catalog)
    assert all("no confirma" in row["nota"] for row in catalog)
    assert len({row["fuente_url"] for row in catalog}) == 4


def test_synthetic_cost_notes_are_explicit_and_not_misleading():
    with SCENARIOS.open("r", encoding="utf-8", newline="") as file:
        data = list(csv.DictReader(file))
    assert len(data) == 300
    assert all("ESCENARIO SINTETICO" in row["notas"] for row in data)
    assert all("no observados" in row["notas"] for row in data)
    assert all("simulada" in row["tienda"].lower() for row in data)


def test_selected_public_prices_are_matched_to_the_correct_product():
    with CATALOG.open("r", encoding="utf-8", newline="") as file:
        catalog = {row["producto_publicado"]: row for row in csv.DictReader(file)}
    reference_prices = {
        "2 Pack Arroz Blanco Selectos 454 g": 1.10,
        "2 Pack Arroz Precocido Selectos 454 g": 1.15,
        "2 Pack Frijol Seda Omoa 1816 g": 11.30,
        "Arroz Salvaje Nomen 250 g": 13.95,
        "Detergente Liquido Rendidor 2 Litros": 4.30,
        "Huevo Mediano Marron Fresco 30 unidades": 5.65,
    }
    for product, price in reference_prices.items():
        assert float(catalog[product]["precio_mostrado_usd"]) == price
