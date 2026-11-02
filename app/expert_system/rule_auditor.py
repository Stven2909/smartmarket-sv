"""Auditoría no destructiva de consistencia y solapamiento entre reglas."""

from collections import Counter
from itertools import combinations, product

from app.expert_system.classifiers import derive_facts
from app.expert_system.models import ProductionRule
from app.expert_system.rule_loader import load_rules
from app.schemas.recommendation import RecommendationRequest
from app.schemas.rule_audit import (
    RuleAuditResponse,
    RuleCoverageSample,
    RuleFinding,
    RulePairOverlap,
)
from app.schemas.versions import RULES_VERSION


def _representative_requests():
    """Recorre clases de límites existentes, sin enumerar precios reales."""

    # Los valores cubren las tres regiones de cada clasificador numérico
    # actual; modificar umbrales requiere revisar estos representantes.
    product_states = (
        (4, 4, 2, 2),  # Todos los productos
        (3, 4, 2, 2),  # Faltan solo opcionales
        (3, 4, 1, 2),  # Falta un esencial
        (2, 4, 1, 2),  # Faltan esenciales y opcionales
        (3, 4, 0, 0),  # Lista sin esenciales
    )
    for cost, saving, extra_km, minutes, stock, stores, promotion in product(
        (40.0, 53.0, 56.0),
        (1.0, 5.0, 11.0),
        (1.0, 4.0, 9.0),
        (10.0, 30.0, 50.0),
        product_states,
        (1, 2, 3),
        (False, True),
    ):
        available, total, essential_available, essential_total = stock
        yield RecommendationRequest(
            request_id="auditoria-reglas",
            alternativa_id="escenario-sintetico",
            costo_total=cost,
            presupuesto=50.0,
            ahorro=saving,
            distancia_km=extra_km + 1.0,
            distancia_adicional_km=extra_km,
            tiempo_estimado_min=minutes,
            productos_disponibles=available,
            productos_totales=total,
            productos_esenciales_disponibles=essential_available,
            productos_esenciales_totales=essential_total,
            numero_supermercados=stores,
            promociones_aplicables=promotion,
        )


def _is_active(rule: ProductionRule, facts: dict[str, bool | float]) -> bool:
    return all(
        type(facts.get(name)) is bool and facts[name] is expected
        for name, expected in rule.conditions.items()
    )


def _before(a: ProductionRule, b: ProductionRule) -> bool:
    return (a.priority, a.id) < (b.priority, b.id)


def audit_rules(rules: list[ProductionRule] | None = None) -> RuleAuditResponse:
    """Separa anomalías estructurales de conflictos previstos por prioridad."""

    checked = sorted(
        list(load_rules() if rules is None else rules),
        key=lambda r: (r.priority, r.id),
    )
    if not checked:
        raise ValueError("La auditoría requiere al menos una regla.")

    findings: list[RuleFinding] = []
    identifiers = Counter(rule.id for rule in checked)
    for identifier, amount in sorted(identifiers.items()):
        if amount > 1:
            findings.append(
                RuleFinding(
                    tipo="ID_DUPLICADO",
                    reglas=[identifier],
                    detalle=f"El identificador {identifier} aparece {amount} veces.",
                )
            )

    for a, b in combinations(checked, 2):
        if a.conditions == b.conditions:
            findings.append(
                RuleFinding(
                    tipo="CONDICIONES_DUPLICADAS",
                    reglas=[a.id, b.id],
                    detalle="Ambas reglas se activan con exactamente las mismas condiciones.",
                )
            )
            if a.result != b.result:
                findings.append(
                    RuleFinding(
                        tipo="SALIDAS_DIVERGENTES",
                        reglas=[a.id, b.id],
                        detalle=(
                            "Las mismas condiciones producen conclusiones o acciones "
                            "diferentes; la prioridad decide cuál se aplica."
                        ),
                    )
                )

        # Una regla general de mayor prioridad siempre impide ganar
        # a una regla específica: inclusión exacta de pares hecho/valor.
        if _before(a, b) and a.conditions.items() <= b.conditions.items():
            findings.append(
                RuleFinding(
                    tipo="REGLA_SOMBREADA",
                    reglas=[a.id, b.id],
                    detalle=(
                        f"Siempre que {b.id} se activa, {a.id} también se activa "
                        "y tiene prioridad; la segunda regla no puede ganar."
                    ),
                )
            )

    counts = Counter({rule.id: 0 for rule in checked})
    pair_counts: Counter[tuple[int, int]] = Counter()
    examples: dict[tuple[int, int], dict[str, object]] = {}
    sample_count = 0

    for request in _representative_requests():
        sample_count += 1
        facts = derive_facts(request)
        active_indices = [
            index for index, rule in enumerate(checked) if _is_active(rule, facts)
        ]
        for index in active_indices:
            counts[checked[index].id] += 1
        for a, b in combinations(active_indices, 2):
            pair = (a, b)
            pair_counts[pair] += 1
            if pair not in examples:
                examples[pair] = request.model_dump(mode="json")

    for rule in checked:
        if counts[rule.id] == 0:
            findings.append(
                RuleFinding(
                    tipo="SIN_ACTIVACION_EN_MUESTRA",
                    reglas=[rule.id],
                    detalle=(
                        "No se activó en las clases sintéticas ensayadas. "
                        "Esto no demuestra que sea lógicamente imposible."
                    ),
                )
            )

    overlaps = [
        RulePairOverlap(
            reglas=[checked[a].id, checked[b].id],
            ganador_por_prioridad=checked[a].id,
            niveles=[checked[a].result.level, checked[b].result.level],
            casos_coincidentes=count,
            ejemplo=examples[(a, b)],
            conflicto_de_nivel=checked[a].result.level != checked[b].result.level,
        )
        for (a, b), count in sorted(pair_counts.items())
    ]

    structural = sum(
        finding.tipo != "SIN_ACTIVACION_EN_MUESTRA" for finding in findings
    )
    return RuleAuditResponse(
        version_reglas=RULES_VERSION,
        reglas_evaluadas=len(checked),
        escenarios_sinteticos=sample_count,
        cobertura=[
            RuleCoverageSample(regla=rule.id, activaciones=counts[rule.id])
            for rule in checked
        ],
        hallazgos=findings,
        solapamientos=overlaps,
        resumen=(
            f"Se evaluaron {len(checked)} reglas en {sample_count} escenarios "
            f"sintéticos. Se identificaron {structural} hallazgos estructurales "
            f"y {len(overlaps)} pares de reglas que pueden coincidir en la muestra. "
            "Los solapamientos no son errores por sí mismos: "
            "la prioridad determina la conclusión."
        ),
        limitaciones=[
            "Los escenarios cubren regiones representativas de los umbrales actuales, "
            "no todos los valores posibles ni una prueba formal de satisfacibilidad.",
            "Una regla no activada en la muestra no implica que sea imposible.",
            "La auditoría no modifica las reglas, los hechos ni las respuestas de compra.",
            "La cantidad de coincidencias depende del muestreo; no es una frecuencia real.",
        ],
    )
