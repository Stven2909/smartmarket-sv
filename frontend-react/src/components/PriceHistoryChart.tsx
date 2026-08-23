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

import { formatMoney } from '../lib/format'
import type { HistorialPrecio } from '../types/domain'

type PriceHistoryChartProps = {
  historial: HistorialPrecio[]
}

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

function buildWideData(historial: HistorialPrecio[]): {
  data: Record<string, string | number | null>[]
  sucursalNames: string[]
} {
  const sucursalMap = new Map<number, string>()

  historial.forEach((item) => {
    const name = item.sucursal?.name ?? `Sucursal ${item.sucursal.id}`
    sucursalMap.set(item.sucursal.id, name)
  })

  const sucursalNames = Array.from(sucursalMap.values())

  const fechaMap = new Map<number, Record<string, string | number | null>>()

  historial.forEach((item) => {
    const ts = new Date(item.fecha).getTime()
    if (!fechaMap.has(ts)) {
      const row: Record<string, string | number | null> = { fecha: item.fecha }
      sucursalNames.forEach((name) => {
        row[name] = null
      })
      fechaMap.set(ts, row)
    }
    const row = fechaMap.get(ts)!
    const sucName = sucursalMap.get(item.sucursal.id) ?? `Sucursal ${item.sucursal.id}`
    row[sucName] = Number(item.precioFinal)
  })

  const data = Array.from(fechaMap.values()).sort((a, b) => {
    const ta = new Date(a.fecha as string).getTime()
    const tb = new Date(b.fecha as string).getTime()
    return ta - tb
  })

  return { data, sucursalNames }
}

function formatFecha(raw: string): string {
  const d = new Date(raw)
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const yy = String(d.getFullYear()).slice(-2)
  return `${dd}/${mm}/${yy}`
}

export const PriceHistoryChart: React.FC<PriceHistoryChartProps> = ({
  historial,
}) => {
  if (!historial || historial.length === 0) {
    return <p className="text-center text-muted-600 pt-8">No hay datos de historial de precios disponibles.</p>
  }

  const { data, sucursalNames } = buildWideData(historial)

  if (sucursalNames.length === 0) {
    return <p className="text-center text-muted-600 pt-8">No se pudieron agrupar los datos por sucursal.</p>
  }

  const labeledData = data.map((row) => ({
    ...row,
    fecha: formatFecha(row.fecha as string),
  }))

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={labeledData} margin={{ top: 20, right: 30, left: 0, bottom: 50 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="fecha" />
        <YAxis
          tickFormatter={(value: number) => formatMoney(value)}
        />
        <Tooltip />
        <Legend verticalAlign="top" height={36} />
        {sucursalNames.map((name, i) => (
          <Line
            key={name}
            type="monotone"
            dataKey={name}
            stroke={COLORS[i % COLORS.length]}
            strokeWidth={2}
            activeDot={{ r: 8 }}
            dot={true}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
