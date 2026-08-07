import { api } from './client'
import type { ApiPaginated, ApiPromocion } from '../types/api'
import { promotionFromApi } from '../types/domain'

// Promociones activas del catálogo. Los datos vienen del backend
// (PrecioActual donde tiene_promocion = true); el frontend solo los ordena.
export async function fetchPromociones(categoriaId?: number, signal?: AbortSignal) {
  const params = new URLSearchParams()
  if (categoriaId) params.set('categoria_id', String(categoriaId))
  const query = params.toString()
  const data = await api.get<ApiPaginated<ApiPromocion>>(`/promociones${query ? `?${query}` : ''}`, signal)
  return data.data
    .map(promotionFromApi)
    .sort((a, b) => (b.discountPercent ?? 0) - (a.discountPercent ?? 0))
}
