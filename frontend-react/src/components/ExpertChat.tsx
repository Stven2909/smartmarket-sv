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

const SUGERENCIAS = [
  '¿Por qué me recomiendas esta alternativa?',
  '¿Cuánto me ahorro?',
  '¿La compra cabe en mi presupuesto?',
  '¿Están todos los productos disponibles?',
  '¿Qué tan lejos queda esta tienda?',
  '¿Cuánto tiempo tardo en llegar?',
  '¿Hay promociones aplicables?',
]

const SMARTY_URL = '/mascota/Smarty_Thinking.webp'

export function ExpertChat({ listaId, resultadoOptimizacionId, sucursalId }: Props) {
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [respuesta, setRespuesta] = useState<ChatResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (resultadoOptimizacionId == null) return null
  const roId = resultadoOptimizacionId

  async function enviar(textoPrevio?: string) {
    const texto = (textoPrevio ?? message).trim()
    if (!texto || loading) return
    setLoading(true)
    setError(null)
    setRespuesta(null)
    try {
      setRespuesta(await chatLista(listaId, roId, sucursalId, texto))
      setMessage('')
    } catch (err) {
      setError(err instanceof Error && err.message ? err.message : 'No pudimos conectar con el asistente.')
    } finally {
      setLoading(false)
    }
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    void enviar()
  }

  // Las preguntas guía están siempre disponibles para que el usuario pueda
  // recorrer los 7 temas; se ocultan solo mientras se espera una respuesta.
  const mostrarSugerencias = !loading

  const avatar = (width: number, height: number, extra?: React.CSSProperties) => (
    <img
      src={SMARTY_URL}
      alt="Smarty"
      style={{
        width,
        height,
        objectFit: 'contain',
        flexShrink: 0,
        ...extra,
      }}
    />
  )

  return (
    <div className="expert-chat" style={{ marginTop: 10 }}>
      {(respuesta || loading) && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 8 }} aria-live="polite">
          {avatar(40, 56)}
          <div
            style={{
              flex: 1,
              padding: '8px 12px',
              borderRadius: 8,
              background: respuesta?.supported ? 'var(--surface, #f9fafb)' : 'rgba(0,0,0,.04)',
              border: '1px solid var(--border, #e5e7eb)',
              fontSize: 12,
              lineHeight: 1.45,
              color: 'var(--text, #111827)',
            }}
          >
            {loading ? 'Estoy revisando los datos de esta alternativa…' : respuesta?.response}
          </div>
        </div>
      )}
      {error && (
        <div style={{ marginBottom: 8, fontSize: 11, color: 'var(--red-700, #b91c1c)' }}>{error}</div>
      )}
      {mostrarSugerencias && (
        <div style={{ marginBottom: 8, paddingLeft: 48 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted, #6b7280)', marginBottom: 4 }}>
            Podés preguntarme, por ejemplo:
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {SUGERENCIAS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => void enviar(s)}
                disabled={loading}
                style={{
                  padding: '4px 8px',
                  borderRadius: 999,
                  border: '1px solid var(--border, #e5e7eb)',
                  background: 'var(--surface, #fff)',
                  fontSize: 11,
                  color: 'var(--brand, #15803d)',
                  cursor: loading ? 'default' : 'pointer',
                }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        {avatar(34, 46, { opacity: 0.9 })}
        <form onSubmit={onSubmit} style={{ display: 'flex', gap: 6, alignItems: 'center', flex: 1 }}>
          <input
            type="text"
            aria-label="Pregunta para Smarty"
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
    </div>
  )
}
