import type { CompararResultado } from '../types/domain'

const LABELS: Record<CompararResultado['procedenciaPrecios'], string> = {
  sincronizados: 'Precios sincronizados',
  simulados: 'Datos simulados (demo)',
  mixtos: 'Precios mixtos',
  manuales: 'Carga manual',
  desconocidos: 'Procedencia no registrada',
}

const ORIGIN_LABELS: Record<string, string> = {
  'html-super-selectos': 'Super Selectos · sincronización web',
  'mock-seeder': 'Datos simulados (demo)',
  manual: 'Carga manual',
}

function fechaActualizacion(value: string | null): string | null {
  if (!value) return null
  const fecha = new Date(value)
  if (Number.isNaN(fecha.getTime())) return null
  return new Intl.DateTimeFormat('es-SV', { dateStyle: 'medium', timeStyle: 'short' }).format(fecha)
}

type Props = {
  resultado: CompararResultado
  compact?: boolean
}

export function PriceProvenance({ resultado, compact = false }: Props) {
  const actualizado = fechaActualizacion(resultado.preciosActualizadosEn)
  const origenes = resultado.origenesPrecio.map((origen) => ORIGIN_LABELS[origen] ?? origen)
  const origenesUnicos = [...new Set(origenes)]
  const mostrarOrigenes = origenesUnicos.length > 1 || (origenesUnicos.length === 1 && origenesUnicos[0] !== LABELS[resultado.procedenciaPrecios])

  return (
    <div className={`price-provenance${compact ? ' compact' : ''}`} aria-label="Procedencia y actualización de precios">
      <span className={`provenance-badge ${resultado.procedenciaPrecios}`}>
        {LABELS[resultado.procedenciaPrecios] ?? resultado.procedenciaPrecios}
      </span>
      {mostrarOrigenes && <span className="provenance-origins">{origenesUnicos.join(' · ')}</span>}
      <span className="provenance-updated">{actualizado ? `Actualizado ${actualizado}` : 'Fecha de actualización no disponible'}</span>
    </div>
  )
}
