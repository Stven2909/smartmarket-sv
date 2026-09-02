import { useState } from 'react'
import { chatLista } from '../api/lists'
import type { ChatResponse } from '../types/domain'

// Asistente explicativo del Sistema Experto. Pregunta sobre la alternativa que
// ya mostró su recomendación (badge). El backend reconstruye los facts y la
// recomendación desde la corrida persistida; aquí solo se envía el mensaje y se
// muestra la respuesta. Si el asistente no está disponible, el backend devuelve
// HTTP 200 con supported:false y un mensaje de fallback que se muestra igual.
type Props = {
  listaId: number
  resultadoOptimizacionId: number | null
  sucursalId: number
}

export function ExpertChat({ listaId, resultadoOptimizacionId, sucursalId }: Props) {
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [respuesta, setRespuesta] = useState<ChatResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (resultadoOptimizacionId == null) return null
  const roId = resultadoOptimizacionId

  async function enviar(e: React.FormEvent) {
    e.preventDefault()
    const texto = message.trim()
    if (!texto || loading) return
    setLoading(true)
    setError(null)
    try {
      setRespuesta(await chatLista(listaId, roId, sucursalId, texto))
      setMessage('')
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : 'No pudimos conectar con el asistente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="expert-chat" style={{ marginTop: 10 }}>
      {respuesta && (
        <div
          style={{
            padding: '8px 12px',
            borderRadius: 8,
            background: respuesta.supported ? 'var(--surface, #f9fafb)' : 'rgba(0,0,0,.04)',
            border: '1px solid var(--border, #e5e7eb)',
            fontSize: 12,
            lineHeight: 1.45,
            marginBottom: 8,
            color: 'var(--text, #111827)',
          }}
        >
          {respuesta.response}
        </div>
      )}
      {error && (
        <div style={{ marginBottom: 8, fontSize: 11, color: 'var(--red-700, #b91c1c)' }}>{error}</div>
      )}
      <form onSubmit={enviar} style={{ display: 'flex', gap: 6 }}>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Preguntá por qué conviene esta alternativa…"
          disabled={loading}
          style={{
            flex: 1,
            padding: '7px 10px',
            borderRadius: 8,
            border: '1px solid var(--border, #e5e7eb)',
            fontSize: 12,
            background: 'var(--surface, #fff)',
          }}
        />
        <button
          type="submit"
          disabled={loading || !message.trim()}
          style={{
            padding: '7px 12px',
            borderRadius: 8,
            border: 'none',
            background: 'var(--green-700, #15803d)',
            color: '#fff',
            fontSize: 12,
            fontWeight: 700,
            cursor: loading ? 'default' : 'pointer',
            opacity: loading || !message.trim() ? 0.6 : 1,
          }}
        >
          {loading ? '…' : 'Preguntar'}
        </button>
      </form>
    </div>
  )
}
