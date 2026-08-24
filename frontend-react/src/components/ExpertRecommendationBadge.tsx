import type { ExpertRecommendation } from '../types/domain'

const NIVEL_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  EXCELENTE: { bg: 'var(--green-100, #dcfce7)', border: 'var(--green-700, #15803d)', text: 'var(--green-700, #15803d)' },
  BUENA: { bg: 'var(--yellow-100, #fef9c3)', border: 'var(--yellow-700, #a16207)', text: 'var(--yellow-700, #a16207)' },
  NO_RECOMENDABLE: { bg: 'var(--red-100, #fee2e2)', border: 'var(--red-700, #b91c1c)', text: 'var(--red-700, #b91c1c)' },
}

const NIVEL_LABELS: Record<string, string> = {
  EXCELENTE: 'Excelente',
  BUENA: 'Buena',
  NO_RECOMENDABLE: 'No recomendable',
}

type Props = {
  recommendation: ExpertRecommendation
}

export function ExpertRecommendationBadge({ recommendation }: Props) {
  const colors = NIVEL_COLORS[recommendation.nivelRecomendacion] ?? NIVEL_COLORS.NO_RECOMENDABLE
  const label = NIVEL_LABELS[recommendation.nivelRecomendacion] ?? recommendation.nivelRecomendacion

  return (
    <div
      className="expert-badge"
      style={{
        background: colors.bg,
        border: `1px solid ${colors.border}`,
        borderRadius: 8,
        padding: '10px 14px',
        marginTop: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 16 }}>🧠</span>
        <span style={{ fontWeight: 800, fontSize: 13, color: colors.text, letterSpacing: '.02em' }}>
          SISTEMA EXPERTO — {label}
        </span>
      </div>

      {recommendation.accionSugerida && (
        <p style={{ margin: '0 0 4px', fontSize: 13, fontWeight: 700 }}>
          {recommendation.accionSugerida}
        </p>
      )}

      {recommendation.explicacion && (
        <p style={{ margin: 0, fontSize: 12, color: 'var(--muted, #6b7280)', lineHeight: 1.4 }}>
          {recommendation.explicacion}
        </p>
      )}

      {(recommendation.indiceConveniencia != null || recommendation.clasificacionConveniencia) && (
        <div style={{ marginTop: 6, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {recommendation.indiceConveniencia != null && (
            <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: 'rgba(0,0,0,.06)', color: 'var(--muted, #6b7280)' }}>
              Índice: {recommendation.indiceConveniencia}
            </span>
          )}
          {recommendation.clasificacionConveniencia && (
            <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: 'rgba(0,0,0,.06)', color: 'var(--muted, #6b7280)' }}>
              {recommendation.clasificacionConveniencia.replace(/_/g, ' ')}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
