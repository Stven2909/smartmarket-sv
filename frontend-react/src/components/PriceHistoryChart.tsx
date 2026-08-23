import React from 'react'
import {
  ResponsiveContainer,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Line,
} from 'recharts'

type PriceHistoryChartProps = {
  historial: ApiHistorialPrecio[]
}

type SerieData = {
  x: number // timestamp en ms
  y: number
  nombre: string
  tipoPromocion?: string | null
}

type GrupoSucursal = {
  nombre: string
  datos: SerieData[]
}

function agruparPorSucursal(historial: ApiHistorialPrecio[]): GrupoSucursal[] {
  // Agrupa los registros por sucursal_id y mapea a datos normalizados
  const mapa = new Map<number, { nombre: string; datos: SerieData[] }>()

  historial.forEach((item) => {
    const sucId = item.sucursal_id
    if (!mapa.has(sucId)) {
      mapa.set(sucId, { nombre: `Sucursal ${sucId}`, datos: [] })
    }
    const entry = mapa.get(sucId)!
    entry.datos.push({
      x: new Date(item.fecha).getTime(),
      y: Number(item.precio_final),
      nombre: item.tipo_promocion ?? '',
      tipoPromocion: item.tipo_promocion,
    })
  })

  mapa.forEach((entry) => {
    entry.datos.sort((a, b) => a.x - b.x)
  })

  return Array.from(mapa.values())
}

export const PriceHistoryChart: React.FC<PriceHistoryChartProps> = ({
  historial,
}) => {
  if (!historial || historial.length === 0) {
    return <p className="text-center text-muted-600 pt-8">No hay datos de historial de precios disponibles.</p>
  }

  const series = agruparPorSucursal(historial)

  if (series.length === 0) {
    return <p className="text-center text-muted-600 pt-8">No se pudieron agrupar los datos por sucursal.</p>
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={series} margin={{ top: 20, right: 30, left: 0, bottom: 50 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="x"
          type="number"
          label={{ value: 'Fecha', angle: -45, offset: 8 }}
        />
        <YAxis
          label={{ value: 'Precio (USD)', angle: -45, offset: 8 }}
        />
        <Tooltip />
        <Legend verticalAlign="top" height={36} />
        {series.map((serie, i) => (
          <Line
            key={i}
            type="line"
            dataKey="y"
            stroke={i === 0 ? '#10b981' : '#0d9668'}
            strokeWidth={2}
            activeDot={{ r: 8 }}
            dot={true}
            label={{ position: 'insideEnd' }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}