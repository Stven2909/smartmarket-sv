import { api } from './client'
import type {
  ApiCategoria,
  ApiHistorialPrecio,
  ApiProductoFull,
  ApiProductoLite,
} from '../types/api'
import { categoryFromApi } from '../types/domain'

export function fetchCategorias(signal?: AbortSignal): Promise<ReturnType<typeof categoryFromApi>[]> {
  return api.get<ApiCategoria[]>('/categorias', signal).then((list) => list.map(categoryFromApi))
}

// Catálogo general (vista "explorar"): índice ligero SIN precios.
export function fetchProductos(page = 1, categoriaId?: number, signal?: AbortSignal) {
  const params = new URLSearchParams({ page: String(page) })
  if (categoriaId) params.set('categoriaId', String(categoriaId))
  return api.get<ApiPaginated<ApiProductoLite>>(`/productos?${params}`, signal)
}

// Buscador: devuelve productos con precios por sucursal.
export function buscarProductos(q: string, page = 1, categoriaId?: number, signal?: AbortSignal) {
  const params = new URLSearchParams({ q, page: String(page) })
  if (categoriaId) params.set('categoriaId', String(categoriaId))
  return api.get<ApiPaginated<ApiProductoFull>>(`/productos/buscar?${params}`, signal)
}

export function fetchProducto(id: number): Promise<ApiProductoFull> {
  return api.get<ApiProductoFull>(`/productos/${id}`)
}

// Historial de precios de un producto (Fase 5): evolución cruda por sucursal,
// devuelto como array plano (sin paginación). El componente PriceHistoryChart
// agrupa los registros por sucursal y muestra líneas independientes por tienda.
export function fetchHistorialPrecios(
  productoId: number,
  signal?: AbortSignal
): Promise<ApiHistorialPrecio[]> {
  return api.get<ApiHistorialPrecio[]>(`/productos/${productoId}/historial`, signal)
}