import type { ExpertRecommendation } from '../types/domain'
import { factLabel, priorityLabel, ruleLabel } from '../lib/expertLabels'

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

function valorHecho(key: string, value: boolean | number): string {
  if (typeof value === 'boolean') return value ? 'Sí' : 'No'
  const formatted = new Intl.NumberFormat('es-SV', { maximumFractionDigits: 2 }).format(value)
  return key.startsWith('porcentaje_') ? `${formatted}%` : formatted
}

function resumirPaso(trace: Record<string, unknown>, index: number): string {
  const rule = [trace.rule_id, trace.rule, trace.regla, trace.id].find((value) => typeof value === 'string') as string | undefined
  const status = [trace.status, trace.result, trace.outcome, trace.estado].find((value) => typeof value === 'string') as string | undefined
  const checked = [trace.conditions_evaluated, trace.condiciones_evaluadas, trace.conditions]
    .find((value) => typeof value === 'number' || Array.isArray(value))
  const count = typeof checked === 'number' ? checked : Array.isArray(checked) ? checked.length : null
  const parts = [rule ? ruleLabel(rule) : `Evaluación ${index + 1}`]
  if (status) parts.push(status)
  if (count !== null) parts.push(`${count} condiciones revisadas`)
  return parts.join(' · ')
}

type Props = {
  recommendation: ExpertRecommendation
}

export function ExpertRecommendationBadge({ recommendation }: Props) {
  const colors = NIVEL_COLORS[recommendation.nivelRecomendacion] ?? NIVEL_COLORS.NO_RECOMENDABLE
  const label = NIVEL_LABELS[recommendation.nivelRecomendacion] ?? recommendation.nivelRecomendacion
  const reglas = [...new Set([
    ...(recommendation.winningRule ? [recommendation.winningRule] : []),
    ...recommendation.reglasActivadas.filter((rule) => rule !== recommendation.winningRule),
  ])]
  const hechos = Object.entries(recommendation.hechosDerivados)

  return (
    <section className="expert-recommendation" style={{ background: colors.bg, borderColor: colors.border }} aria-label="Evaluación del Sistema Experto">
      <div className="expert-recommendation-title">
        <span aria-hidden="true">🧠</span>
        <b style={{ color: colors.text }}>Sistema Experto · {label}</b>
      </div>
      {recommendation.accionSugerida && <p className="expert-recommendation-action">{recommendation.accionSugerida}</p>}
      {recommendation.explicacion && <p className="expert-recommendation-explanation">{recommendation.explicacion}</p>}

      {reglas.length > 0 && (
        <div className="expert-rule-chips" aria-label="Reglas activadas">
          {reglas.slice(0, 3).map((rule) => <span key={rule} className={rule === recommendation.winningRule ? 'winning-rule-chip' : undefined}>{ruleLabel(rule)}{rule === recommendation.winningRule ? ' · decisiva' : ''}</span>)}
          {reglas.length > 3 && <span>+{reglas.length - 3} reglas</span>}
        </div>
      )}

      {(recommendation.indiceConveniencia != null || recommendation.clasificacionConveniencia) && (
        <div className="expert-recommendation-metrics">
          {recommendation.indiceConveniencia != null && <span>Índice {recommendation.indiceConveniencia}</span>}
          {recommendation.clasificacionConveniencia && <span>{recommendation.clasificacionConveniencia.replace(/_/g, ' ')}</span>}
        </div>
      )}

      <details className="expert-reasoning-details">
        <summary>Cómo llegó a esta conclusión</summary>
        <div className="expert-reasoning-content">
          {recommendation.winningRule && (
            <p><b>Regla decisiva:</b> {ruleLabel(recommendation.winningRule)}</p>
          )}
          {recommendation.prioridadAplicada && (
            <p><b>Prioridad aplicada:</b> {priorityLabel(recommendation.prioridadAplicada)}</p>
          )}
          <p><b>Versión de reglas:</b> {recommendation.versionReglas || 'No informada'}</p>
          {recommendation.losingRules.length > 0 && (
            <p><b>Otras reglas evaluadas:</b> {recommendation.losingRules.map(ruleLabel).join(', ')}</p>
          )}
          {hechos.length > 0 && (
            <div>
              <b>Datos que consideró</b>
              <dl className="expert-facts-list">
                {hechos.map(([key, value]) => (
                  <div key={key}><dt>{factLabel(key)}</dt><dd>{valorHecho(key, value)}</dd></div>
                ))}
              </dl>
            </div>
          )}
          {recommendation.trace.length > 0 && (
            <div>
              <b>Resumen de evaluación</b>
              <ol className="expert-trace-list">
                {recommendation.trace.map((step, index) => <li key={index}>{resumirPaso(step, index)}</li>)}
              </ol>
            </div>
          )}
        </div>
      </details>
    </section>
  )
}
