"""Exportación PDF opcional del sistema experto; no altera /recommend."""

from fastapi import APIRouter, Response

from app.schemas.evidence_report import EvidenceReportRequest
from app.services.evidence_report_service import generate_evidence_pdf

router = APIRouter(prefix="/api/v1", tags=["evidence"])


@router.post(
    "/evidence-report",
    response_class=Response,
    summary="Genera un PDF con trazas, ranking, auditoría y sensibilidad",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Informe académico PDF descargable.",
        }
    },
)
def create_evidence_report(request: EvidenceReportRequest) -> Response:
    pdf = generate_evidence_pdf(request)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="smartmarket-evidencias.pdf"',
            "Cache-Control": "no-store",
        },
    )
