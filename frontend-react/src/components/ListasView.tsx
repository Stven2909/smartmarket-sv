import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import * as listsApi from '../api/lists'
import { buscarProductos } from '../api/catalog'
import { formatMoney } from '../lib/format'
import { productFromApi } from '../types/domain'
import type { CompararResultado, ListaDetalle, ListaSummary, OptimizarResultado, Promotion } from '../types/domain'
import { ProductCard } from './ProductCard'
import { SearchBox } from './SearchBox'
import { ExpertChat } from './ExpertChat'
import { ExpertRecommendationBadge } from './ExpertRecommendationBadge'
import { LocationConsentDialog } from './LocationConsentDialog'

type Tab = 'activa' | 'completada'

type Props = {
  onListasChange: (listas: ListaSummary[]) => void
}

export function ListasView({ onListasChange }: Props) {
  const [tab, setTab] = useState<Tab>('activa')
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
  const [resultadoOptimizacionId, setResultadoOptimizacionId] = useState<number | null>(null)
  const [lat, setLat] = useState('')
  const [lng, setLng] = useState('')
  const [geolocating, setGeolocating] = useState(false)
  const [locationConsentOpen, setLocationConsentOpen] = useState(false)
  const [locationNotice, setLocationNotice] = useState<string | null>(null)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [locationSource, setLocationSource] = useState<'device' | 'manual' | null>(null)
  const locationNoticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => {
    if (locationNoticeTimer.current) clearTimeout(locationNoticeTimer.current)
  }, [])

  // promociones de la lista activa (Fase 5)
  const [promociones, setPromociones] = useState<Promotion[]>([])
  const [promosError, setPromosError] = useState<string | null>(null)
  const [promosLoading, setPromosLoading] = useState(false)

  const refreshListas = useCallback(async () => {
    const data = await listsApi.fetchListas(tab)
    setListas(data)
    if (tab === 'activa') onListasChange(data)
    return data
  }, [tab, onListasChange])

  useEffect(() => {
    refreshListas().catch(() => setError('No se pudieron cargar tus listas.'))
  }, [refreshListas])

  async function switchTab(next: Tab) {
    if (next === tab) return
    setTab(next)
    setSelectedId(null)
    setDetalles([])
    setComparacion(null)
    setOptimizacion(null)
    setResultadoOptimizacionId(null)
    setPromociones([])
    setPromosError(null)
    setError(null)
    try {
      const data = await listsApi.fetchListas(next)
      setListas(data)
      if (next === 'activa') onListasChange(data)
    } catch {
      setError('No se pudieron cargar las listas.')
    }
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await listsApi.createLista(newNombre, newPresupuesto ? Number(newPresupuesto) : undefined)
      setNewNombre('')
      setNewPresupuesto('')
      if (tab === 'completada') await switchTab('activa')
      else await refreshListas()
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
    setResultadoOptimizacionId(null)
    setPromociones([])
    setPromosError(null)
    setError(null)
    try {
      const lista = await listsApi.fetchLista(id)
      setDetalles(lista.detalles)
      setPresupuesto(lista.presupuesto)
      if (tab === 'activa') {
        setPromosLoading(true)
        try {
          setPromociones(await listsApi.fetchPromocionesDeLista(id))
        } catch (e) {
          setPromosError(e instanceof ApiError ? e.message : 'No se pudieron cargar las promociones de esta lista.')
        } finally {
          setPromosLoading(false)
        }
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo cargar la lista.')
    }
  }

  async function runCompletar() {
    if (!selectedId) return
    if (!window.confirm('¿Marcar esta lista como comprada? Podrás reactivarla después si te equivocas.')) return
    setBusy(true)
    setError(null)
    try {
      await listsApi.completarLista(selectedId)
      setSelectedId(null)
      setDetalles([])
      await refreshListas()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo completar la lista.')
    } finally {
      setBusy(false)
    }
  }

  async function runReactivar() {
    if (!selectedId) return
    if (!window.confirm('¿Reactivar esta lista? Volverá a estar activa para seguir editándola.')) return
    setBusy(true)
    setError(null)
    try {
      await listsApi.reactivarLista(selectedId)
      setSelectedId(null)
      setDetalles([])
      await refreshListas()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo reactivar la lista.')
    } finally {
      setBusy(false)
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
    setResultadoOptimizacionId(null)
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
      setLocationError('Agrega las coordenadas o usa tu ubicación para calcular la mejor alternativa.')
      return
    }
    setLocationError(null)
    setComparacion(null)
    setOptimizacion(null)
    setResultadoOptimizacionId(null)
    setError(null)
    setLocationNotice(null)
    try {
      const data = await listsApi.optimizarLista(selectedId, latValue, lngValue)
      setOptimizacion(data.resultados)
      setResultadoOptimizacionId(data.resultadoOptimizacionId)
      if (locationSource === 'device') {
        setLocationNotice('Ahora el sistema está usando tu ubicación para calcular la mejor alternativa.')
        if (locationNoticeTimer.current) clearTimeout(locationNoticeTimer.current)
        locationNoticeTimer.current = setTimeout(() => setLocationNotice(null), 4500)
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo optimizar.')
    }
  }

  function useGeolocation() {
    setLocationConsentOpen(true)
  }

  function confirmUseGeolocation() {
    setLocationConsentOpen(false)
    if (!('geolocation' in navigator)) {
      setLocationError('Tu navegador no admite ubicación. Puedes ingresar las coordenadas manualmente.')
      return
    }
    setGeolocating(true)
    setLocationError(null)
    setError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6))
        setLng(pos.coords.longitude.toFixed(6))
        setLocationSource('device')
        setGeolocating(false)
      },
      () => {
        setGeolocating(false)
        setLocationError('No pudimos obtener tu ubicación. Revisa el permiso o ingresa las coordenadas manualmente.')
      },
    )
  }

  const isActiveTab = tab === 'activa'
  const selectedList = listas.find((lista) => lista.id === selectedId)

  return (
    <section className="real-basket-panel">
      <div className="section-title-row">
        <div>
          <div className="eyebrow"><span />MIS LISTAS DE COMPRA</div>
          <h2>Crea, compara y optimiza</h2>
        </div>
      </div>

      <div className="category-filters" style={{ marginBottom: 18 }}>
        <button type="button" className={tab === 'activa' ? 'active' : ''} onClick={() => void switchTab('activa')}>
          Activas
        </button>
        <button type="button" className={tab === 'completada' ? 'active' : ''} onClick={() => void switchTab('completada')}>
          Completadas
        </button>
      </div>

      {error && <div className="live-error"><b>Aviso</b><span>{error}</span></div>}

      {locationConsentOpen && (
        <LocationConsentDialog
          description="SmartMarket usará tus coordenadas para calcular distancias y tiempos de viaje. No las guardamos en tu cuenta. Tu navegador también te pedirá permiso."
          onCancel={() => setLocationConsentOpen(false)}
          onConfirm={confirmUseGeolocation}
        />
      )}

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
          <span>{tab === 'activa' ? '📝' : '✅'}</span>
          <h3>{tab === 'activa' ? 'No tienes listas activas' : 'Aún no has completado ninguna compra'}</h3>
          <p>
            {tab === 'activa'
              ? 'Crea tu primera lista para empezar a comparar precios.'
              : 'Cuando marques una lista como comprada, aparecerá aquí como parte de tu historial.'}
          </p>
        </div>
      )}

      {listas.length > 0 && (
        <div className="list-select-grid" role="group" aria-label="Seleccionar lista de compras">
          {listas.map((lista) => (
            <button
              key={lista.id}
              type="button"
              className={`list-select-card${selectedId === lista.id ? ' active' : ''}`}
              aria-pressed={selectedId === lista.id}
              onClick={() => selectLista(lista.id)}
            >
              <span className="list-select-status">{tab === 'completada' ? '✓ Compra completada' : 'Lista activa'}</span>
              <strong>{lista.nombre}</strong>
              <span className="list-select-meta">
                {lista.detallesCount} {lista.detallesCount === 1 ? 'producto' : 'productos'}
                {lista.presupuesto != null && ` · Presupuesto ${formatMoney(lista.presupuesto)}`}
              </span>
            </button>
          ))}
        </div>
      )}

      {selectedId !== null && (
        <>
          {selectedList && (
            <div className="selected-list-heading">
              <div>
                <span className="eyebrow">{tab === 'completada' ? 'COMPRA DEL HISTORIAL' : 'TU LISTA'}</span>
                <h2>{selectedList.nombre}</h2>
              </div>
              <span className="selected-list-count">
                {selectedList.detallesCount} {selectedList.detallesCount === 1 ? 'producto' : 'productos'}
              </span>
            </div>
          )}
          <div className="real-basket-layout">
            <div className="real-basket-items">
              {detalles.length === 0 && (
                <div className="empty-state compact">
                  <span>🛒</span>
                  <h3>Lista vacía</h3>
                  <p>{isActiveTab ? 'Busca productos abajo y agrégalos a esta lista.' : 'Esta compra no tenía productos registrados.'}</p>
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
                  {isActiveTab ? (
                    <>
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
                    </>
                  ) : (
                    <span className="quantity-control"><b>{detalle.cantidad}</b> un.</span>
                  )}
                </article>
              ))}

              <div className="quick-total">
                <span>Presupuesto: {presupuesto != null ? formatMoney(presupuesto) : 'sin definir'}</span>
              </div>

              {isActiveTab && (
                <>
                  <div className="category-filters list-primary-actions">
                    <button type="button" className="add-button" onClick={runComparar}>Comparar precios</button>
                    <div className="tooltip-anchor">
                      <button
                        type="button"
                        className="add-button optimize-action"
                        onClick={runOptimizar}
                        aria-describedby="optimize-purchase-tooltip"
                      >
                        Optimizar compra
                      </button>
                      <span id="optimize-purchase-tooltip" role="tooltip" className="action-tooltip">
                        Compara costo, distancia, tiempo y promociones; muestra la evaluación del Sistema Experto. Usa tu ubicación o coordenadas manuales.
                      </span>
                    </div>
                    <button type="button" className="load-more-button" onClick={runCompletar} disabled={busy}>
                      Marcar como completada
                    </button>
                  </div>
                  {locationError && (
                    <div className="location-inline-error" role="alert">
                      <span aria-hidden="true">!</span>
                      <div>
                        <b>No se pudo optimizar</b>
                        <p>{locationError}</p>
                      </div>
                    </div>
                  )}

                  <div className="basket-location-panel">
                    <span>UBICACIÓN OPCIONAL</span>
                    <p>Para optimizar necesitamos latitud y longitud. No guardamos coordenadas.</p>
                    <div className="basket-location-controls">
                      <input
                        type="text"
                        value={lat}
                        onChange={(e) => { setLat(e.target.value); setLocationSource('manual'); setLocationError(null) }}
                        placeholder="Latitud (ej. 13.6989)"
                      />
                      <input
                        type="text"
                        value={lng}
                        onChange={(e) => { setLng(e.target.value); setLocationSource('manual'); setLocationError(null) }}
                        placeholder="Longitud (ej. -89.1914)"
                      />
                      <button type="button" className="add-button" onClick={useGeolocation} disabled={geolocating}>
                        {geolocating ? 'Obteniendo…' : 'Usar mi ubicación'}
                      </button>
                    </div>
                    {locationNotice && <div className="location-status-toast" role="status">📍 {locationNotice}</div>}
                  </div>

                  {(promosLoading || promociones.length > 0 || promosError) && (
                    <div className="optimizer-panel" style={{ marginTop: 18 }}>
                      <div className="optimizer-head">
                        <span className="spark-icon">🏷️</span>
                        <div>
                          <span>PROMOCIONES DE ESTA LISTA</span>
                          <h2>Ofertas de tus productos</h2>
                        </div>
                      </div>
                      {promosLoading && <div className="live-loading"><i />Buscando ofertas…</div>}
                      {!promosLoading && promosError && (
                        <div className="live-error"><b>Promociones no disponibles</b><span>{promosError}</span></div>
                      )}
                      {!promosLoading && !promosError && promociones.length === 0 && (
                        <div className="empty-optimizer">
                          <span>🏷️</span>
                          <h3>Sin promociones para esta lista</h3>
                        </div>
                      )}
                      {!promosLoading && promociones.length > 0 && (
                        <div className="promotions-grid">
                          {promociones.map((promo) => (
                            <article key={promo.id} className="promotion-card">
                              <div className="promotion-visual">
                                <span className="promotion-emoji">{promo.categoryIcon}</span>
                                {promo.discountPercent != null && (
                                  <span className="promotion-badge">-{promo.discountPercent}%</span>
                                )}
                              </div>
                              <div className="promotion-body">
                                <span className="promotion-time">{promo.supermarketName} · {promo.branchName}</span>
                                <h3>{promo.productName}</h3>
                                <p>{promo.unitLabel}</p>
                                <div className="promotion-price">
                                  {promo.previousPrice != null && <s>{formatMoney(promo.previousPrice)}</s>}
                                  <b>{formatMoney(promo.price)}</b>
                                  {promo.savings != null && (
                                    <span className="live-saving">Ahorras {formatMoney(promo.savings)}</span>
                                  )}
                                </div>
                              </div>
                            </article>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}

              {!isActiveTab && (
                <div className="category-filters">
                  <button type="button" className="load-more-button" onClick={runReactivar} disabled={busy}>
                    Reactivar lista
                  </button>
                </div>
              )}

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
                          {r.beneficioPromociones > 0 && ` · ahorro ${formatMoney(r.beneficioPromociones)}`}
                          {r.dentroDelPresupuesto === false && ' · excede presupuesto'}
                        </small>
                      </div>
                      <b className="recommendation-total">{formatMoney(r.costoTotal)}</b>
                    </article>
                  ))}
                </div>
              )}

              {optimizacion !== null && optimizacion.length > 0 && (
                <div className="optimizer-panel">
                  <div className="optimizer-head">
                    <span className="spark-icon">🧠</span>
                    <div>
                      <span>ANÁLISIS DEL SISTEMA EXPERTO</span>
                      <h2>Alternativas recomendadas</h2>
                      <p>El optimizador ordena las opciones; el experto explica sus ventajas y condiciones.</p>
                    </div>
                  </div>
                  {optimizacion.map((r) => (
                    <article key={r.sucursalId} className={`recommendation-card${optimizacion[0].sucursalId === r.sucursalId ? ' best' : ''}`}>
                      <div>
                        <span className="recommendation-label">{r.supermercado}</span>
                        <span className="recommendation-store">{r.sucursal}</span>
                        <small>
                          {formatMoney(r.costoTotal)} · {r.distanciaKm != null ? `${r.distanciaKm.toFixed(1)} km` : '—'} · {r.tiempoMinutos != null ? `${r.tiempoMinutos} min` : '—'} · ahorro promos {formatMoney(r.beneficioPromociones)}
                        </small>
                        {r.expertRecommendation && (
                          <>
                            <ExpertRecommendationBadge recommendation={r.expertRecommendation} />
                            {selectedId != null && (
                              <ExpertChat
                                listaId={selectedId}
                                resultadoOptimizacionId={resultadoOptimizacionId}
                                sucursalId={r.sucursalId}
                              />
                            )}
                          </>
                        )}
                        {r.expertRecommendation?.chatbotAvailable === false && (
                          <div style={{ marginTop: 4, fontSize: 10, color: 'var(--muted, #6b7280)', fontStyle: 'italic' }}>
                            El asistente explicativo no está disponible temporalmente, pero la recomendación principal continúa disponible.
                          </div>
                        )}
                        {!r.expertSystemAvailable && (
                          <div style={{ marginTop: 6, fontSize: 11, color: 'var(--muted, #6b7280)' }}>
                            🧠 Sistema Experto no disponible
                          </div>
                        )}
                      </div>
                      <b className="recommendation-total">Score {r.score}</b>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </div>

          {isActiveTab && (
            <>
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
        </>
      )}
    </section>
  )
}
