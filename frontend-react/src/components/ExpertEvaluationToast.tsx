type Props = {
  visible: boolean
}

export function ExpertEvaluationToast({ visible }: Props) {
  if (!visible) return null

  return (
    <div className="expert-result-toast" role="status" aria-live="polite">
      <span className="expert-result-toast-icon" aria-hidden="true">🧠</span>
      <div>
        <b>Análisis del Sistema Experto listo</b>
        <span>Evaluó costo, distancia, tiempo y promociones.</span>
      </div>
      <span className="expert-result-toast-check" aria-hidden="true">✓</span>
    </div>
  )
}
