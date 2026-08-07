import { api } from './client'
import type {
  ApiComparar,
  ApiDetalle,
  ApiLista,
  ApiListaShow,
  ApiOptimizar,
  ApiPaginated,
  ApiPromocion,
} from '../types/api'
import {
  compararResultadoFromApi,
  listaFromApi,
  listaShowFromApi,
  optimizarResultadoFromApi,
  promotionFromApi,
} from '../types/domain'
import type { CompararResultado, ListaDetalle, ListaSummary, OptimizarResultado, Promotion } from '../types/domain'

export type ListaDetallada = ListaSummary & { detalles: ListaDetalle[] }

export async function fetchListas(estado?: string, page = 1): Promise<ListaSummary[]> {
  const params = new URLSearchParams({ page: String(page) })
  if (estado) params.set('estado', estado)
  const data = await api.get<ApiPaginated<ApiLista>>(`/listas?${params}`)
  return data.data.map(listaFromApi)
}

export async function createLista(nombre: string, presupuesto?: number): Promise<ListaSummary> {
  const data = await api.post<ApiLista>('/listas', { nombre, presupuesto })
  return listaFromApi(data)
}

export async function fetchLista(id: number): Promise<ListaDetallada> {
  const data = await api.get<ApiListaShow>(`/listas/${id}`)
  return listaShowFromApi(data)
}

export async function destroyLista(id: number): Promise<void> {
  await api.del(`/listas/${id}`)
}

export async function completarLista(id: number): Promise<ListaSummary> {
  const data = await api.patch<ApiLista>(`/listas/${id}/completar`)
  return listaFromApi(data)
}

export async function reactivarLista(id: number): Promise<ListaSummary> {
  const data = await api.patch<ApiLista>(`/listas/${id}/reactivar`)
  return listaFromApi(data)
}

export async function fetchPromocionesDeLista(listaId: number): Promise<Promotion[]> {
  const data = await api.get<ApiPromocion[]>(`/listas/${listaId}/promociones`)
  return data.map(promotionFromApi)
}

export async function addProductoToLista(listaId: number, productoId: number, cantidad = 1, esencial = true) {
  await api.post<ApiDetalle>(`/listas/${listaId}/productos`, { producto_id: productoId, cantidad, esencial })
}

export async function updateProductoEnLista(listaId: number, detalleId: number, cantidad: number, esencial: boolean) {
  await api.patch<ApiDetalle>(`/listas/${listaId}/productos/${detalleId}`, { cantidad, esencial })
}

export async function removeProductoDeLista(listaId: number, detalleId: number): Promise<void> {
  await api.del(`/listas/${listaId}/productos/${detalleId}`)
}

export async function compararLista(listaId: number): Promise<{ nombre: string; presupuesto: number | null; resultados: CompararResultado[] }> {
  const data = await api.get<ApiComparar>(`/listas/${listaId}/comparar`)
  return {
    nombre: data.lista,
    presupuesto: data.presupuesto,
    resultados: data.resultados.map(compararResultadoFromApi),
  }
}

export async function optimizarLista(
  listaId: number,
  lat: number,
  lng: number,
): Promise<{ nombre: string; presupuesto: number | null; mejorOpcion: OptimizarResultado | null; resultados: OptimizarResultado[] }> {
  const data = await api.get<ApiOptimizar>(`/listas/${listaId}/optimizar?lat=${lat}&lng=${lng}`)
  return {
    nombre: data.lista,
    presupuesto: data.presupuesto,
    mejorOpcion: data.mejor_opcion ? optimizarResultadoFromApi(data.mejor_opcion) : null,
    resultados: data.resultados.map(optimizarResultadoFromApi),
  }
}
