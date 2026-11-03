import type { OptimizarResultado } from '../types/domain'
import { ExpertChat } from './ExpertChat'

type Props = {
  listaId: number
  resultadoOptimizacionId: number | null
  alternatives: OptimizarResultado[]
  selectedSucursalId: number | null
  onSelectSucursal: (sucursalId: number) => void
}

export function ExpertChatPanel({ listaId, resultadoOptimizacionId, alternatives, selectedSucursalId, onSelectSucursal }: Props) {
  const evaluadas = alternatives.filter((result) => result.expertSystemAvailable && result.expertRecommendation)
  if (evaluadas.length === 0) return null

  const selected = evaluadas.find((result) => result.sucursalId === selectedSucursalId) ?? evaluadas[0]

  return (
    <section className="expert-chat-panel" aria-label="Chat con el Sistema Experto">
      <div className="expert-chat-panel-heading">
        <span aria-hidden="true">💬</span>
        <div><b>Pregunta sobre una alternativa</b><p>El experto responde usando los datos de la evaluación seleccionada.</p></div>
      </div>
      <label className="expert-alternative-select">
        <span>Alternativa evaluada</span>
        <select value={selected.sucursalId} onChange={(event) => onSelectSucursal(Number(event.target.value))}>
          {evaluadas.map((result) => (
            <option key={result.sucursalId} value={result.sucursalId}>
              {result.supermercado} · {result.sucursal}
            </option>
          ))}
        </select>
      </label>
      {resultadoOptimizacionId == null ? (
        <p className="expert-chat-pending">El chat estará disponible cuando se guarde la evaluación.</p>
      ) : (
        <ExpertChat
          key={`${listaId}-${resultadoOptimizacionId}-${selected.sucursalId}`}
          listaId={listaId}
          resultadoOptimizacionId={resultadoOptimizacionId}
          sucursalId={selected.sucursalId}
        />
      )}
    </section>
  )
}
