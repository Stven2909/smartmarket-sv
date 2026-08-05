import { api } from './client'
import type {
  ApiCategoria,
  ApiPaginated,
  ApiProductoFull,
  ApiProductoLite,
  ApiSucursal,
} from '../types/api'
import { branchFromApi, categoryFromApi } from '../types/domain'

export function fetchCategorias(signal?: AbortSignal): Promise<ReturnType<typeof categoryFromApi>[]> {
  return api.get<ApiCategoria[]>('/categorias', signal).then((list) => list.map(categoryFromApi))
}

// Catálogo general (vista "explorar"): índice ligero SIN precios.
export function fetchProductos(page = 1, categoriaId?: number, signal?: AbortSignal) {
  const params = new URLSearchParams({ page: String(page) })
  if (categoriaId) params.set('categoria_id', String(categoriaId))
  return api.get<ApiPaginated<ApiProductoLite>>(`/productos?${params}`, signal)
}

// Buscador: devuelve productos con precios por sucursal.
export function buscarProductos(q: string, page = 1, categoriaId?: number, signal?: AbortSignal) {
  const params = new URLSearchParams({ q, page: String(page) })
  if (categoriaId) params.set('categoria_id', String(categoriaId))
  return api.get<ApiPaginated<ApiProductoFull>>(`/productos/buscar?${params}`, signal)
}

export function fetchProducto(id: number): Promise<ApiProductoFull> {
  return api.get<ApiProductoFull>(`/productos/${id}`)
}

export function fetchSucursales(): Promise<ReturnType<typeof branchFromApi>[]> {
  return api.get<ApiSucursal[]>('/sucursales').then((list) => list.map(branchFromApi))
}
