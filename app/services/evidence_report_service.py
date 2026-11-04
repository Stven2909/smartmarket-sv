"""Documento PDF reproducible de evidencia técnica, sin datos externos."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

from app.expert_system.classifiers import THRESHOLDS, THRESHOLDS_VERSION
from app.expert_system.convenience_config import (
    CONVENIENCE_CONFIG_VERSION,
    DEFAULT_CONVENIENCE_CONFIG,
)
from app.expert_system.rule_auditor import audit_rules
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.schemas.evidence_report import EvidenceReportRequest
from app.schemas.rule_audit import RuleAuditResponse
from app.schemas.sensitivity import SensitivityRequest, SensitivityResponse
from app.schemas.versions import CONTRACT_VERSION, RULES_VERSION
from app.services.comparison_service import compare_alternatives
from app.services.sensitivity_service import analyze_sensitivity

INK = colors.HexColor("#193230")
GREEN = colors.HexColor("#126457")
PALE = colors.HexColor("#EDF5F2")
LINE = colors.HexColor("#D7E5E0")
WHITE = colors.white
PAGE_WIDTH = A4[0] - 84


@dataclass(frozen=True)
class EvidenceBundle:
    """Todos los resultados proceden de los servicios públicos existentes."""

    request: EvidenceReportRequest
    comparison: ComparisonResponse
    audit: RuleAuditResponse
    sensitivity: list[SensitivityResponse]


def build_evidence(request: EvidenceReportRequest) -> EvidenceBundle:
    """Reutiliza el motor sin duplicar inferencia ni modificar hechos."""

    comparison = compare_alternatives(
        ComparisonRequest(
            alternativas=[scenario.hechos for scenario in request.escenarios]
        )
    )
    return EvidenceBundle(
        request=request,
        comparison=comparison,
        audit=audit_rules(),
        sensitivity=[
            analyze_sensitivity(SensitivityRequest(alternativa=scenario.hechos))
            for scenario in request.escenarios
        ],
    )


def _styles() -> dict[str, ParagraphStyle]:
    original = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SMTitle", parent=original["Title"], fontName="Helvetica-Bold",
            fontSize=22, leading=27, textColor=INK, spaceAfter=14,
        ),
        "heading": ParagraphStyle(
            "SMSection", parent=original["Heading2"], fontName="Helvetica-Bold",
            fontSize=12, leading=16, textColor=GREEN, spaceBefore=15,
            spaceAfter=8, keepWithNext=True,
        ),
        "subheading": ParagraphStyle(
            "SMSubheading", parent=original["Heading3"], fontName="Helvetica-Bold",
            fontSize=9.8, leading=13, textColor=INK, spaceBefore=10,
            spaceAfter=5, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "SMBody", parent=original["BodyText"], fontName="Helvetica",
            fontSize=9, leading=13, textColor=INK, spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "SMSmall", parent=original["BodyText"], fontName="Helvetica",
            fontSize=7.4, leading=10, textColor=INK, spaceAfter=5,
        ),
        "table": ParagraphStyle(
            "SMTable", parent=original["BodyText"], fontName="Helvetica",
            fontSize=7.1, leading=9, textColor=INK,
        ),
        "tablehead": ParagraphStyle(
            "SMTableHead", parent=original["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.2, leading=9.2, textColor=WHITE,
        ),
        "kicker": ParagraphStyle(
            "SMKicker", parent=original["BodyText"], fontName="Helvetica-Bold",
            fontSize=8.5, leading=11, textColor=GREEN, spaceAfter=9,
        ),
        "center": ParagraphStyle(
            "SMCenter", parent=original["BodyText"], alignment=TA_CENTER,
            fontSize=7.5, leading=10, textColor=INK,
        ),
    }


def _paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    text = escape(str(value)).replace("\n", "<br/>")
    return Paragraph(text, style)


def _table(
    rows: list[list[object]], widths: list[float], styles: dict[str, ParagraphStyle]
) -> Table:
    wrapped = [
        [
            _paragraph(value, styles["tablehead"] if index == 0 else styles["table"])
            for value in row
        ]
        for index, row in enumerate(rows)
    ]
    table = Table(wrapped, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _heading(story: list, text: str, styles: dict, sub: bool = False) -> None:
    story.append(_paragraph(text, styles["subheading" if sub else "heading"]))


def _footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(LINE)
    canvas.line(42, 31, width - 42, 31)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(INK)
    canvas.drawString(42, 20, "SmartMarket SV | Evidencia técnica de reglas")
    canvas.drawRightString(width - 42, 20, f"Página {doc.page}")
    canvas.restoreState()


def _summary(
    bundle: EvidenceBundle, story: list, styles: dict, created: datetime
) -> None:
    comparison = bundle.comparison
    reports = [row.recomendacion for row in comparison.ranking]
    levels = Counter(item.nivel_recomendacion for item in reports)
    active = Counter(rule for item in reports for rule in item.reglas_activadas)
    wins = Counter(item.winning_rule for item in reports if item.winning_rule)
    overlaps = sum(len(item.reglas_activadas) > 1 for item in reports)
    no_rule = sum(item.winning_rule is None for item in reports)
    origin = (
        "Escenarios declarados sintéticos por el solicitante."
        if bundle.request.procedencia == "sintetico"
        else "Procedencia declarada no verificada por este servicio."
    )

    story.append(_paragraph("SMARTMARKET SV / EVIDENCIA ACADÉMICA", styles["kicker"]))
    story.append(_paragraph("Informe técnico de inferencia y validación", styles["title"]))
    story.append(
        _paragraph(
            f"Generado (UTC): {created.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Contrato: {CONTRACT_VERSION} | Reglas: {RULES_VERSION} | "
            f"Clasificadores: {THRESHOLDS_VERSION} | "
            f"Índice: {CONVENIENCE_CONFIG_VERSION}",
            styles["small"],
        )
    )
    story.append(_paragraph(origin, styles["body"]))
    story.append(
        _paragraph(
            "El informe reúne hechos recibidos, decisiones R01-R11, condiciones "
            "auditadas, ranking, sensibilidad y verificación de consistencia. "
            "El índice auxiliar no modifica la regla ganadora. "
            "Las pruebas son deterministas y no acreditan precisión comercial.",
            styles["body"],
        )
    )

    _heading(story, "1. Resumen del conjunto de casos", styles)
    metrics = [
        ["Alternativas", "Excelentes", "Buenas", "No recomendables"],
        [
            len(reports),
            levels["EXCELENTE"],
            levels["BUENA"],
            levels["NO_RECOMENDABLE"],
        ],
    ]
    story.append(_table(metrics, [PAGE_WIDTH / 4] * 4, styles))
    story.append(
        _paragraph(
            f"Sin regla ganadora: {no_rule}. Casos con varias reglas activas: "
            f"{overlaps}. Reglas activadas en el conjunto: {len(active)}/11.",
            styles["body"],
        )
    )

    _heading(story, "2. Comparación experta", styles)
    story.append(_paragraph(comparison.criterio_orden, styles["small"]))
    rows = [["Pos.", "Alternativa", "Nivel", "Regla", "Índice"]]
    for option in comparison.ranking:
        result = option.recomendacion
        rows.append(
            [
                option.posicion,
                option.alternativa_id,
                result.nivel_recomendacion,
                result.winning_rule or "Sin regla",
                f"{result.indice_conveniencia:.2f}/100",
            ]
        )
    story.append(_table(rows, [39, 153, 130, 80, PAGE_WIDTH - 402], styles))
    for warning in comparison.advertencias:
        story.append(_paragraph("Advertencia: " + warning, styles["small"]))

    _heading(story, "3. Cobertura de las reglas con los casos aportados", styles)
    story.append(
        _table(
            [
                ["Regla", "Activaciones", "Victorias", "Interpretación"]
            ] + [
                [
                    f"R{index:02}",
                    active[f"R{index:02}"],
                    wins[f"R{index:02}"],
                    "Activada" if active[f"R{index:02}"] else "Sin activación",
                ]
                for index in range(1, 9)
            ],
            [75, 100, 85, PAGE_WIDTH - 260],
            styles,
        )
    )
    story.append(
        _paragraph(
            "La cobertura refleja únicamente los casos suministrados en esta "
            "solicitud; no constituye una prueba exhaustiva.",
            styles["small"],
        )
    )


def _knowledge(bundle: EvidenceBundle, story: list, styles: dict) -> None:
    audit = bundle.audit
    story.append(PageBreak())
    _heading(story, "4. Auditoría de consistencia del conocimiento", styles)
    story.append(_paragraph(audit.resumen, styles["body"]))
    rows = [["Métrica de auditoría", "Resultado"]]
    rows.extend(
        [
            ["Reglas", str(audit.reglas_evaluadas)],
            ["Escenarios representativos", str(audit.escenarios_sinteticos)],
            ["Hallazgos reportados", str(len(audit.hallazgos))],
            ["Pares con solapamientos", str(len(audit.solapamientos))],
        ]
    )
    story.append(_table(rows, [PAGE_WIDTH * 0.65, PAGE_WIDTH * 0.35], styles))
    if audit.hallazgos:
        _heading(story, "Hallazgos que deben revisarse", styles, sub=True)
        story.append(
            _table(
                [["Tipo", "Reglas", "Detalle"]]
                + [
                    [issue.tipo, ", ".join(issue.reglas), issue.detalle]
                    for issue in audit.hallazgos
                ],
                [120, 85, PAGE_WIDTH - 205],
                styles,
            )
        )
    else:
        story.append(
            _paragraph(
                "No se detectaron anomalías estructurales en las reglas actuales "
                "con los chequeos implementados.",
                styles["body"],
            )
        )
    _heading(story, "Solapamientos detectados en la muestra sintética", styles, sub=True)
    story.append(
        _table(
            [["Par", "Ganadora", "Niveles", "Coincidencias", "Nivel diferente"]]
            + [
                [
                    " / ".join(pair.reglas),
                    pair.ganador_por_prioridad,
                    " / ".join(pair.niveles),
                    pair.casos_coincidentes,
                    "Sí" if pair.conflicto_de_nivel else "No",
                ]
                for pair in audit.solapamientos
            ],
            [65, 80, 160, 94, PAGE_WIDTH - 399],
            styles,
        )
    )
    story.append(
        _paragraph(
            "Un solapamiento no equivale a un error: las reglas ganan por "
            "prioridad numérica y, si empatan, por identificador.",
            styles["small"],
        )
    )
    _heading(story, "Parámetros utilizados", styles)
    story.append(
        _table(
            [["Umbral", "Valor"]]
            + [[key, value] for key, value in sorted(THRESHOLDS.items())],
            [PAGE_WIDTH * 0.65, PAGE_WIDTH * 0.35],
            styles,
        )
    )
    _heading(story, "Pesos del índice auxiliar", styles, sub=True)
    story.append(
        _table(
            [["Factor", "Peso"]]
            + [
                [name, f"{weight * 100:.1f}%"]
                for name, weight in DEFAULT_CONVENIENCE_CONFIG.weights().items()
            ],
            [PAGE_WIDTH * 0.65, PAGE_WIDTH * 0.35],
            styles,
        )
    )


def _scenario_details(bundle: EvidenceBundle, story: list, styles: dict) -> None:
    results = {
        row.alternativa_id: row.recomendacion for row in bundle.comparison.ranking
    }

    for index, (scenario, sensitivity) in enumerate(
        zip(bundle.request.escenarios, bundle.sensitivity, strict=True),
        start=1,
    ):
        result = results[scenario.hechos.alternativa_id]
        facts = scenario.hechos
        story.append(PageBreak())
        _heading(story, f"5.{index}. Escenario: {scenario.nombre}", styles)
        story.append(
            _paragraph(
                f"Alternativa: {facts.alternativa_id} | "
                f"Solicitud: {facts.request_id} | "
                f"Nivel: {result.nivel_recomendacion} | "
                f"Regla: {result.winning_rule or 'Sin regla'} | "
                f"Índice: {result.indice_conveniencia:.2f}/100",
                styles["body"],
            )
        )
        _heading(story, "Hechos de entrada", styles, sub=True)
        story.append(
            _table(
                [["Hecho", "Valor", "Hecho", "Valor"]]
                + [
                    [
                        "Costo",
                        f"{facts.costo_total:.2f}",
                        "Presupuesto",
                        f"{facts.presupuesto:.2f}",
                    ],
                    [
                        "Ahorro informado",
                        f"{facts.ahorro:.2f}",
                        "Distancia (km)",
                        f"{facts.distancia_km:.2f}",
                    ],
                    [
                        "Distancia adicional",
                        f"{facts.distancia_adicional_km:.2f}",
                        "Tiempo (min)",
                        str(facts.tiempo_estimado_min),
                    ],
                    [
                        "Productos",
                        f"{facts.productos_disponibles}/{facts.productos_totales}",
                        "Esenciales",
                        (
                            f"{facts.productos_esenciales_disponibles}/"
                            f"{facts.productos_esenciales_totales}"
                        ),
                    ],
                    [
                        "Supermercados",
                        str(facts.numero_supermercados),
                        "Promociones",
                        "Sí" if facts.promociones_aplicables else "No",
                    ],
                ],
                [135, 85, 155, PAGE_WIDTH - 375],
                styles,
            )
        )
        _heading(story, "Conclusión y justificación", styles, sub=True)
        story.append(_paragraph(result.explicacion, styles["body"]))
        story.append(_paragraph("Acción: " + result.accion_sugerida, styles["small"]))
        story.append(
            _paragraph(
                "Reglas activadas: "
                + (", ".join(result.reglas_activadas) or "Ninguna")
                + ". Prioridad: " + result.prioridad_aplicada + ".",
                styles["small"],
            )
        )
        _heading(story, "Trazabilidad de las once reglas", styles, sub=True)
        story.append(
            _table(
                [["Regla", "Se activó", "Incumplimientos"]]
                + [
                    [
                        item["rule_id"],
                        "Sí" if item["activated"] else "No",
                        ", ".join(item["unmatched_conditions"]) or "Ninguno",
                    ]
                    for item in result.trace
                ],
                [70, 100, PAGE_WIDTH - 170],
                styles,
            )
        )
        _heading(story, "Desglose del índice auxiliar", styles, sub=True)
        story.append(
            _table(
                [["Factor", "Peso", "Valor normalizado", "Puntos"]]
                + [
                    [
                        name,
                        f"{weight * 100:.1f}%",
                        f"{result.componentes_conveniencia[name]:.3f}",
                        (
                            f"{weight * result.componentes_conveniencia[name] * 100:.2f}"
                        ),
                    ]
                    for name, weight in result.pesos_conveniencia.items()
                ],
                [150, 80, 135, PAGE_WIDTH - 365],
                styles,
            )
        )
        _heading(story, "Sensibilidad hipotética", styles, sub=True)
        story.append(
            _paragraph(sensitivity.interpretacion, styles["small"])
        )
        story.append(
            _table(
                [["Escenario", "Nivel", "Regla", "Cambio índice", "Cambió"]]
                + [
                    [
                        item.escenario,
                        item.recomendacion.nivel_recomendacion,
                        item.recomendacion.winning_rule or "Ninguna",
                        f"{item.diferencia_indice:+.2f}",
                        "Sí" if item.cambia_decision else "No",
                    ]
                    for item in sensitivity.escenarios
                ],
                [140, 117, 70, 103, PAGE_WIDTH - 430],
                styles,
            )
        )


def generate_evidence_pdf(request: EvidenceReportRequest) -> bytes:
    """Compila el informe sin IO externo, sin almacenamiento y sin ejecución libre."""

    evidence = build_evidence(request)
    now = datetime.now(timezone.utc)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=42,
        rightMargin=42,
        topMargin=43,
        bottomMargin=45,
        title="SmartMarket SV - Informe académico de evidencia técnica",
        author="SmartMarket SV | Sistema experto Python",
    )
    styles = _styles()
    story: list = []
    _summary(evidence, story, styles, now)
    _knowledge(evidence, story, styles)
    _scenario_details(evidence, story, styles)
    story.append(PageBreak())
    _heading(story, "6. Alcance y limitaciones", styles)
    for text in [
        "Este informe documenta el comportamiento del software frente a los "
        "hechos suministrados y las reglas cargadas al momento de generarlo.",
        "La procedencia de los hechos es una declaración del solicitante; "
        "Python no comprueba precios, inventarios ni establecimientos.",
        "Los 3402 escenarios de la auditoría son sintéticos y representan "
        "regiones de los umbrales. No demuestran exactitud comercial ni una "
        "verificación lógica universal de todos los datos posibles.",
        "Las variaciones de sensibilidad no son predicciones, probabilidades "
        "ni recomendaciones de precios futuros.",
        "Los resultados del comparador Python no sustituyen la optimización "
        "económica independiente del backend Laravel.",
        "La reproducción exige conservar este documento, el contrato de "
        "hechos, las versiones de reglas y la configuración de umbrales.",
    ]:
        story.append(_paragraph(text, styles["body"]))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
