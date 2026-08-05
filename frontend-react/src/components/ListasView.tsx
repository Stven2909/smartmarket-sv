import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import * as listsApi from '../api/lists'
import { buscarProductos } from '../api/catalog'
import { productFromApi } from '../types/domain'
import type { CompararResultado, ListaDetalle, ListaSummary, OptimizarResultado } from '../types/domain'
import { ProductCard } from './ProductCard'
import { SearchBox } from './SearchBox'

function money(value: number): string {
  return value.toLocaleString('es-SV', { style: 'currency', currency: 'USD' })
}

type Props = {
  onListasChange: (listas: ListaSummary[]) => void
}

export function ListasView({ onListasChange }: Props) {
  const [listas, setListas] = useState<ListaSummary[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [detalles, setDetalles] = useState<ListaDetalle[]>([])
  const [presupuesto, setPresupuesto] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // formulario de nueva lista
  const [newNombre, setNewNombre] = useState('')
  const [newPresupuesto, setNewPresupuesto] = useState('')

  // buscador para agregar productos
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ReturnType<typeof productFromApi>[]>([])
  const [searchError, setSearchError] = useState<string | null>(null)

  // comparación y optimización
  const [comparacion, setComparacion] = useState<CompararResultado[] | null>(null)
  const [optimizacion, setOptimizacion] = useState<OptimizarResultado[] | null>(null)
  const [lat, setLat] = useState('')
  const [lng, setLng] = useState('')
  const [geolocating, setGeolocating] = useState(false)

  const refreshListas = useCallback(async () => {
    const data = await listsApi.fetchListas()
    setListas(data)
    onListasChange(data)
    return data
  }, [onListasChange])

  useEffect(() => {
    refreshListas().catch(() => setError('No se pudieron cargar tus listas.'))
  }, [refreshListas])

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await listsApi.createLista(newNombre, newPresupuesto ? Number(newPresupuesto) : undefined)
      setNewNombre('')
      setNewPresupuesto('')
      await refreshListas()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo crear la lista.')
    } finally {
      setBusy(false)
    }
  }

  async function selectLista(id: number) {
    setSelectedId(id)
    setComparacion(null)
    setOptimizacion(null)
    setError(null)
    try {
      const lista = await listsApi.fetchLista(id)
      setDetalles(lista.detalles)
      setPresupuesto(lista.presupuesto)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo cargar la lista.')
    }
  }

  async function runSearch() {
    setSearchError(null)
    try {
      const data = await buscarProductos(query)
      setResults(data.data.map(productFromApi))
    } catch (e) {
      setSearchError(e instanceof ApiError ? e.message : 'Error al buscar.')
    }
  }

  async function addProduct(productoId: number) {
    if (!selectedId) return
    setBusy(true)
    try {
      await listsApi.addProductoToLista(selectedId, productoId)
      const lista = await listsApi.fetchLista(selectedId)
      setDetalles(lista.detalles)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo agregar el producto.')
    } finally {
      setBusy(false)
    }
  }

  async function changeCantidad(detalle: ListaDetalle, cantidad: number) {
    if (!selectedId || cantidad < 1) return
    try {
      await listsApi.updateProductoEnLista(selectedId, detalle.id, cantidad, detalle.esencial)
      const lista = await listsApi.fetchLista(selectedId)
      setDetalles(lista.detalles)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo actualizar.')
    }
  }

  async function toggleEsencial(detalle: ListaDetalle) {
    if (!selectedId) return
    try {
      await listsApi.updateProductoEnLista(selectedId, detalle.id, detalle.cantidad, !detalle.esencial)
      const lista = await listsApi.fetchLista(selectedId)
      setDetalles(lista.detalles)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo actualizar.')
    }
  }

  async function removeDetalle(detalleId: number) {
    if (!selectedId) return
    try {
      await listsApi.removeProductoDeLista(selectedId, detalleId)
      const lista = await listsApi.fetchLista(selectedId)
      setDetalles(lista.detalles)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo quitar el producto.')
    }
  }

  async function runComparar() {
    if (!selectedId) return
    setComparacion(null)
    setOptimizacion(null)
    setError(null)
    try {
      const data = await listsApi.compararLista(selectedId)
      setComparacion(data.resultados)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo comparar.')
    }
  }

  async function runOptimizar() {
    if (!selectedId) return
    const latValue = Number(lat)
    const lngValue = Number(lng)
    if (!latValue || !lngValue) {
      setError('Necesitas latitud y longitud para optimizar.')
      return
    }
    setComparacion(null)
    setOptimizacion(null)
    setError(null)
    try {
      const data = await listsApi.optimizarLista(selectedId, latValue, lngValue)
      setOptimizacion(data.resultados)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo optimizar.')
    }
  }

  function useGeolocation() {
    if (!('geolocation' in navigator)) {
      setError('Tu navegador no soporta geolocalización.')
      return
    }
    setGeolocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6))
        setLng(pos.coords.longitude.toFixed(6))
        setGeolocating(false)
      },
      () => {
        setGeolocating(false)
        setError('No pudimos obtener tu ubicación.')
      },
    )
  }

  return (
    <section className="real-basket-panel">
      <div className="section-title-row">
        <div>
          <div className="eyebrow"><span />MIS LISTAS DE COMPRA</div>
          <h2>Crea, compara y optimiza</h2>
        </div>
      </div>

      {error && <div className="live-error"><b>Aviso</b><span>{error}</span></div>}

      <form className="auth-form" onSubmit={handleCreate}>
        <div className="category-filters">
          <input
            type="text"
            value={newNombre}
            onChange={(e) => setNewNombre(e.target.value)}
            placeholder="Nombre de la lista (ej. Canasta semanal)"
            required
            maxLength={150}
            className="search-box"
          />
          <input
            type="number"
            value={newPresupuesto}
            onChange={(e) => setNewPresupuesto(e.target.value)}
            placeholder="Presupuesto $ (opcional)"
            min={0}
            step="0.01"
            className="search-box"
          />
          <button type="submit" className="add-button" disabled={busy}>Crear lista</button>
        </div>
      </form>

      {listas.length === 0 && (
        <div className="empty-state compact">
          <span>📝</span>
          <h3>No tienes listas todavía</h3>
          <p>Crea tu primera lista para empezar a comparar precios.</p>
        </div>
      )}

      {listas.length > 0 && (
        <div className="category-filters">
          {listas.map((lista) => (
            <button
              key={lista.id}
              type="button"
              className={selectedId === lista.id ? 'active' : ''}
              onClick={() => selectLista(lista.id)}
            >
              {lista.nombre} · {lista.detallesCount}
            </button>
          ))}
        </div>
      )}

      {selectedId !== null && (
        <>
          <div className="real-basket-layout">
            <div className="real-basket-items">
              {detalles.length === 0 && (
                <div className="empty-state compact">
                  <span>🛒</span>
                  <h3>Lista vacía</h3>
                  <p>Busca productos abajo y agrégalos a esta lista.</p>
                </div>
              )}
              {detalles.map((detalle) => (
                <article key={detalle.id} className="product-card">
                  <div className="product-main">
                    <span className="product-emoji">🛒</span>
                    <div className="product-title-line">
                      <h3>{detalle.nombre}</h3>
                      <p>{detalle.categoria}</p>
                    </div>
                    <span className={`limited-chip${detalle.esencial ? ' essential' : ''}`}>
                      {detalle.esencial ? 'Esencial' : 'Opcional'}
                    </span>
                  </div>
                  <div className="quantity-control">
                    <button type="button" onClick={() => changeCantidad(detalle, detalle.cantidad - 1)}>-</button>
                    <span>{detalle.cantidad}</span>
                    <button type="button" onClick={() => changeCantidad(detalle, detalle.cantidad + 1)}>+</button>
                  </div>
                  <button type="button" className="link-button" onClick={() => toggleEsencial(detalle)}>
                    Marcar {detalle.esencial ? 'opcional' : 'esencial'}
                  </button>
                  <button type="button" className="link-button danger" onClick={() => removeDetalle(detalle.id)}>
                    Quitar
                  </button>
                </article>
              ))}

              <div className="quick-total">
                <span>Presupuesto: {presupuesto != null ? money(presupuesto) : 'sin definir'}</span>
              </div>

              <div className="category-filters">
                <button type="button" className="add-button" onClick={runComparar}>Comparar precios</button>
                <button type="button" className="add-button" onClick={runOptimizar}>Optimizar compra</button>
              </div>

              <div className="basket-location-panel">
                <span>UBICACIÓN OPCIONAL</span>
                <p>Para optimizar necesitamos latitud y longitud. No guardamos coordenadas.</p>
                <div className="basket-location-controls">
                  <input
                    type="text"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                    placeholder="Latitud (ej. 13.6989)"
                  />
                  <input
                    type="text"
                    value={lng}
                    onChange={(e) => setLng(e.target.value)}
                    placeholder="Longitud (ej. -89.1914)"
                  />
                  <button type="button" className="add-button" onClick={useGeolocation} disabled={geolocating}>
                    {geolocating ? 'Obteniendo…' : 'Usar mi ubicación'}
                  </button>
                </div>
              </div>

              {comparacion !== null && (
                <div className="optimizer-panel">
                  <div className="optimizer-head">
                    <span className="spark-icon">💡</span>
                    <div>
                      <span>COMPARACIÓN DE PRECIOS</span>
                      <h2>Costo por supermercado</h2>
                    </div>
                  </div>
                  {comparacion.length === 0 && (
                    <div className="empty-optimizer"><span>🛒</span><h3>Sin precios disponibles</h3></div>
                  )}
                  {comparacion.map((r) => (
                    <article key={r.sucursalId} className="recommendation-card">
                      <div>
                        <span className="recommendation-label">{r.supermercado}</span>
                        <span className="recommendation-store">{r.sucursal}</span>
                        <small>
                          {r.esencialesDisponibles}/{r.esencialesTotales} esenciales
                          {r.beneficioPromociones > 0 && ` · ahorro ${money(r.beneficioPromociones)}`}
                          {r.dentroDelPresupuesto === false && ' · excede presupuesto'}
                        </small>
                      </div>
                      <b className="recommendation-total">{money(r.costoTotal)}</b>
                    </article>
                  ))}
                </div>
              )}

              {optimizacion !== null && optimizacion.length > 0 && (
                <div className="optimizer-panel">
                  <div className="optimizer-head">
                    <span className="spark-icon">🎯</span>
                    <div>
                      <span>MEJOR ALTERNATIVA (SCORE)</span>
                      <h2>Menor score = mejor compra</h2>
                    </div>
                  </div>
                  {optimizacion.map((r) => (
                    <article key={r.sucursalId} className={`recommendation-card${optimizacion[0].sucursalId === r.sucursalId ? ' best' : ''}`}>
                      <div>
                        <span className="recommendation-label">{r.supermercado}</span>
                        <span className="recommendation-store">{r.sucursal}</span>
                        <small>
                          {money(r.costoTotal)} · {r.distanciaKm.toFixed(1)} km · {r.tiempoMinutos} min · ahorro promos {money(r.beneficioPromociones)}
                        </small>
                      </div>
                      <b className="recommendation-total">Score {r.score}</b>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="conversation-search">
            <SearchBox query={query} setQuery={setQuery} onSubmit={runSearch} placeholder="Agregar productos a esta lista…" />
          </div>
          {searchError && <div className="live-error"><b>Búsqueda fallida</b><span>{searchError}</span></div>}
          {results.length > 0 && (
            <div className="live-products">
              {results.map((product) => (
                <ProductCard key={product.id} product={product} onAddToList={() => addProduct(product.id)} />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}
