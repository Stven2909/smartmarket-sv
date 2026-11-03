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
import { ExpertChatPanel } from './ExpertChatPanel'
import { ExpertRecommendationBadge } from './ExpertRecommendationBadge'
import { LocationConsentDialog } from './LocationConsentDialog'
import { ExpertEvaluationToast } from './ExpertEvaluationToast'
import { PriceProvenance } from './PriceProvenance'
import { EXPERT_LEVEL_LABELS, omissionReasonLabel } from '../lib/expertLabels'

type Tab = 'activa' | 'completada'

type Props = {
  onListasChange: (listas: ListaSummary[]) => void
}

export function ListasView({ onListasChange }: Props) {
  const [tab, setTab] = useState<Tab>('activa')
  const [listas, setListas] = useState<ListaSummary[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const selectedIdRef = useRef<number | null>(null)
  selectedIdRef.current = selectedId
  const [detalles, setDetalles] = useState<ListaDetalle[]>([])
  const [presupuesto, setPresupuesto] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const detailRequestId = useRef(0)
  const [editorOpen, setEditorOpen] = useState(false)

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
  const [optimizationLoading, setOptimizationLoading] = useState(false)
  const [expertEvaluatedNotice, setExpertEvaluatedNotice] = useState(false)
  const [comparisonLoading, setComparisonLoading] = useState(false)
  const [comparisonOpen, setComparisonOpen] = useState(false)
  const [chatSucursalId, setChatSucursalId] = useState<number | null>(null)
  const [optimizationTimestamp, setOptimizationTimestamp] = useState<string | null>(null)
  const [decisionStale, setDecisionStale] = useState(false)
  const firstLocationInputRef = useRef<HTMLInputElement>(null)
  const geolocationRequestId = useRef(0)
  const optimizationRequestId = useRef(0)
  const comparisonRequestId = useRef(0)
  const expertNoticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [lat, setLat] = useState('')
  const [lng, setLng] = useState('')
  const [geolocating, setGeolocating] = useState(false)
  const [locationConsentOpen, setLocationConsentOpen] = useState(false)
  const [locationNotice, setLocationNotice] = useState<string | null>(null)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [locationPanelOpen, setLocationPanelOpen] = useState(false)
  const locationPanelRef = useRef<HTMLDetailsElement>(null)
  const [locationSource, setLocationSource] = useState<'device' | 'manual' | null>(null)
  const locationNoticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => {
    if (locationNoticeTimer.current) clearTimeout(locationNoticeTimer.current)
    if (expertNoticeTimer.current) clearTimeout(expertNoticeTimer.current)
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
    detailRequestId.current += 1
    selectedIdRef.current = null
    geolocationRequestId.current += 1
    optimizationRequestId.current += 1
    comparisonRequestId.current += 1
    setTab(next)
    setSelectedId(null)
    setGeolocating(false)
    setDetalles([])
    setEditorOpen(false)
    setDetailLoading(false)
    setOptimizationLoading(false)
    setComparisonLoading(false)
    setComparacion(null)
    setOptimizacion(null)
    setResultadoOptimizacionId(null)
    setChatSucursalId(null)
    setOptimizationTimestamp(null)
    setDecisionStale(false)
    setQuery('')
    setResults([])
    setSearchError(null)
    setComparisonOpen(false)
    setPromociones([])
    setPromosLoading(false)
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
    const requestId = ++detailRequestId.current
    selectedIdRef.current = id
    geolocationRequestId.current += 1
    setGeolocating(false)
    optimizationRequestId.current += 1
    comparisonRequestId.current += 1
    setSelectedId(id)
    setDetalles([])
    setEditorOpen(false)
    setDetailLoading(true)
    setOptimizationLoading(false)
    setComparisonLoading(false)
    setComparacion(null)
    setOptimizacion(null)
    setResultadoOptimizacionId(null)
    setChatSucursalId(null)
    setOptimizationTimestamp(null)
    setDecisionStale(false)
    setQuery('')
    setResults([])
    setSearchError(null)
    setComparisonOpen(false)
    setPromociones([])
    setPromosError(null)
    setError(null)
    setExpertEvaluatedNotice(false)
    try {
      const lista = await listsApi.fetchLista(id)
      if (requestId !== detailRequestId.current) return
      setDetalles(lista.detalles)
      setEditorOpen(lista.detalles.length === 0)
      setPresupuesto(lista.presupuesto)
      if (tab === 'activa') {
        setPromosLoading(true)
        try {
          const data = await listsApi.fetchPromocionesDeLista(id)
          if (requestId === detailRequestId.current) setPromociones(data)
        } catch (e) {
          if (requestId === detailRequestId.current) setPromosError(e instanceof ApiError ? e.message : 'No se pudieron cargar las promociones de esta lista.')
        } finally {
          if (requestId === detailRequestId.current) setPromosLoading(false)
        }
      }
    } catch (e) {
      if (requestId === detailRequestId.current) setError(e instanceof ApiError ? e.message : 'No se pudo cargar la lista.')
    } finally {
      if (requestId === detailRequestId.current) setDetailLoading(false)
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
    const requestListId = selectedId
    setSearchError(null)
    try {
      const data = await buscarProductos(query)
      if (requestListId === selectedIdRef.current) setResults(data.data.map(productFromApi))
    } catch (e) {
      if (requestListId === selectedIdRef.current) setSearchError(e instanceof ApiError ? e.message : 'Error al buscar.')
    }
  }

  function invalidateDecision() {
    if (optimizacion !== null || comparacion !== null) setDecisionStale(true)
    optimizationRequestId.current += 1
    comparisonRequestId.current += 1
    setComparacion(null)
    setOptimizacion(null)
    setResultadoOptimizacionId(null)
    setChatSucursalId(null)
    setOptimizationTimestamp(null)
    setExpertEvaluatedNotice(false)
  }

  async function addProduct(productoId: number) {
    if (!selectedId) return
    const listId = selectedId
    invalidateDecision()
    setBusy(true)
    try {
      await listsApi.addProductoToLista(listId, productoId)
      const lista = await listsApi.fetchLista(listId)
      if (selectedIdRef.current === listId) setDetalles(lista.detalles)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo agregar el producto.')
    } finally {
      setBusy(false)
    }
  }

  async function changeCantidad(detalle: ListaDetalle, cantidad: number) {
    if (!selectedId || cantidad < 1) return
    const listId = selectedId
    invalidateDecision()
    try {
      await listsApi.updateProductoEnLista(listId, detalle.id, cantidad, detalle.esencial)
      const lista = await listsApi.fetchLista(listId)
      if (selectedIdRef.current === listId) setDetalles(lista.detalles)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo actualizar.')
    }
  }

  async function toggleEsencial(detalle: ListaDetalle) {
    if (!selectedId) return
    const listId = selectedId
    invalidateDecision()
    try {
      await listsApi.updateProductoEnLista(listId, detalle.id, detalle.cantidad, !detalle.esencial)
      const lista = await listsApi.fetchLista(listId)
      if (selectedIdRef.current === listId) setDetalles(lista.detalles)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo actualizar.')
    }
  }

  async function removeDetalle(detalleId: number) {
    if (!selectedId) return
    const listId = selectedId
    invalidateDecision()
    try {
      await listsApi.removeProductoDeLista(listId, detalleId)
      const lista = await listsApi.fetchLista(listId)
      if (selectedIdRef.current === listId) {
        setDetalles(lista.detalles)
        if (lista.detalles.length === 0) setEditorOpen(true)
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo quitar el producto.')
    }
  }

  async function runComparar() {
    if (!selectedId) return
    const listId = selectedId
    const requestId = ++comparisonRequestId.current
    optimizationRequestId.current += 1
    setComparisonLoading(true)
    setOptimizationLoading(false)
    setComparacion(null)
    setOptimizacion(null)
    setResultadoOptimizacionId(null)
    setError(null)
    setComparisonOpen(true)
    setChatSucursalId(null)
    setOptimizationTimestamp(null)
    setDecisionStale(false)
    try {
      const data = await listsApi.compararLista(listId)
      if (requestId === comparisonRequestId.current) setComparacion(data.resultados)
    } catch (e) {
      if (requestId === comparisonRequestId.current) setError(e instanceof ApiError ? e.message : 'No se pudo comparar.')
    } finally {
      if (requestId === comparisonRequestId.current) setComparisonLoading(false)
    }
  }

  async function runOptimizar() {
    if (!selectedId) return
    const latValue = Number(lat)
    const lngValue = Number(lng)
    if (!lat.trim() || !lng.trim()) {
      setLocationError(null)
      setLocationPanelOpen(true)
      requestAnimationFrame(() => {
        locationPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        firstLocationInputRef.current?.focus({ preventScroll: true })
      })
      return
    }
    if (!Number.isFinite(latValue) || latValue < -90 || latValue > 90 || !Number.isFinite(lngValue) || lngValue < -180 || lngValue > 180) {
      setLocationError('Revisa las coordenadas: latitud entre −90 y 90 y longitud entre −180 y 180.')
      setLocationPanelOpen(true)
      return
    }
    setLocationError(null)
    const listId = selectedId
    const requestId = ++optimizationRequestId.current
    comparisonRequestId.current += 1
    setComparacion(null)
    setOptimizacion(null)
    setResultadoOptimizacionId(null)
    setChatSucursalId(null)
    setOptimizationTimestamp(null)
    setComparisonOpen(false)
    setError(null)
    setLocationNotice(null)
    setExpertEvaluatedNotice(false)
    setOptimizationLoading(true)
    setComparisonLoading(false)
    try {
      const data = await listsApi.optimizarLista(listId, latValue, lngValue)
      if (requestId !== optimizationRequestId.current) return
      setOptimizacion(data.resultados)
      setResultadoOptimizacionId(data.resultadoOptimizacionId)
      const mejorEvaluada = data.resultados
        .filter((resultado) => resultado.expertSystemAvailable && resultado.expertRecommendation)
        .sort((a, b) => a.score - b.score)[0]
      setChatSucursalId(mejorEvaluada?.sucursalId ?? null)
      setOptimizationTimestamp(new Date().toISOString())
      setDecisionStale(false)
      if (data.resultados.some((resultado) => resultado.expertSystemAvailable && resultado.expertRecommendation)) {
        setExpertEvaluatedNotice(true)
        if (expertNoticeTimer.current) clearTimeout(expertNoticeTimer.current)
        expertNoticeTimer.current = setTimeout(() => setExpertEvaluatedNotice(false), 5200)
      }
      if (locationSource === 'device') {
        setLocationNotice('Ahora el sistema está usando tu ubicación para calcular la mejor alternativa.')
        if (locationNoticeTimer.current) clearTimeout(locationNoticeTimer.current)
        locationNoticeTimer.current = setTimeout(() => setLocationNotice(null), 4500)
      }
    } catch (e) {
      if (requestId === optimizationRequestId.current) setError(e instanceof ApiError ? e.message : 'No se pudo optimizar.')
    } finally {
      if (requestId === optimizationRequestId.current) setOptimizationLoading(false)
    }
  }

  function useGeolocation() {
    setLocationConsentOpen(true)
  }

  function confirmUseGeolocation() {
    setLocationConsentOpen(false)
    const listId = selectedIdRef.current
    const requestId = ++geolocationRequestId.current
    if (!('geolocation' in navigator)) {
      setLocationError('Tu navegador no admite ubicación. Puedes ingresar las coordenadas manualmente.')
      return
    }
    setGeolocating(true)
    setLocationError(null)
    setError(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (requestId !== geolocationRequestId.current || selectedIdRef.current !== listId) return
        setLat(pos.coords.latitude.toFixed(6))
        setLng(pos.coords.longitude.toFixed(6))
        setLocationSource('device')
        setGeolocating(false)
      },
      () => {
        if (requestId !== geolocationRequestId.current || selectedIdRef.current !== listId) return
        setGeolocating(false)
        setLocationError('No pudimos obtener tu ubicación. Revisa el permiso o ingresa las coordenadas manualmente.')
      },
    )
  }

  const isActiveTab = tab === 'activa'
  const selectedList = listas.find((lista) => lista.id === selectedId)

  return (
    <section className="real-basket-panel">
      <ExpertEvaluationToast visible={expertEvaluatedNotice} />
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
            <header className="selected-list-heading decision-list-heading" key={`heading-${selectedId}`}>
              <div>
                <span className="eyebrow">{tab === 'completada' ? 'COMPRA DEL HISTORIAL' : 'TU LISTA'}</span>
                <h2>{selectedList.nombre}</h2>
                <div className="selected-list-meta">
                  <span>{selectedList.detallesCount} {selectedList.detallesCount === 1 ? 'producto' : 'productos'}</span>
                  <span>{selectedList.presupuesto != null ? `Presupuesto ${formatMoney(selectedList.presupuesto)}` : 'Sin presupuesto definido'}</span>
                  {optimizationTimestamp && <span>Última optimización {new Intl.DateTimeFormat('es-SV', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(optimizationTimestamp))}</span>}
                </div>
              </div>
            </header>
          )}
          <div className="real-basket-layout" key={`detail-${selectedId}`}>
            <div className="real-basket-items">
              {detailLoading && <div className="list-detail-loading" role="status"><i /> Cargando el contenido de tu lista…</div>}
              {!detailLoading && (
                <details className="list-section list-editor" open={editorOpen} onToggle={(event) => setEditorOpen(event.currentTarget.open)}>
                  <summary>
                    <span><b>Productos de la lista</b><small>{detalles.length} artículos · presupuesto {presupuesto != null ? formatMoney(presupuesto) : 'sin definir'}</small></span>
                    <span className="disclosure-indicator" aria-hidden="true">⌄</span>
                  </summary>
                  <div className="list-section-content">
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
                            <button type="button" className="link-button danger" onClick={() => removeDetalle(detalle.id)}>Quitar</button>
                          </>
                        ) : <span className="quantity-control"><b>{detalle.cantidad}</b> un.</span>}
                      </article>
                    ))}
                    {isActiveTab && (
                      <>
                        <div className="conversation-search">
                          <SearchBox query={query} setQuery={setQuery} onSubmit={runSearch} placeholder="Agregar productos a esta lista…" />
                        </div>
                        {searchError && <div className="live-error"><b>Búsqueda fallida</b><span>{searchError}</span></div>}
                        {results.length > 0 && (
                          <div className="live-products">
                            {results.map((product) => <ProductCard key={product.id} product={product} onAddToList={() => addProduct(product.id)} />)}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </details>
              )}

              {isActiveTab && (
                <>
                  <div className="category-filters list-primary-actions">
                    <button type="button" className="add-button" onClick={runComparar} disabled={detailLoading || detalles.length === 0 || comparisonLoading || optimizationLoading}>
                      {comparisonLoading ? <><span className="button-spinner" aria-hidden="true" /> Comparando…</> : 'Comparar precios'}
                    </button>
                    <div className="tooltip-anchor">
                      <button
                        type="button"
                        className="add-button optimize-action"
                        onClick={runOptimizar}
                        disabled={detailLoading || detalles.length === 0 || optimizationLoading || comparisonLoading}
                        aria-describedby="optimize-purchase-tooltip"
                        aria-busy={optimizationLoading}
                      >
                        {optimizationLoading ? <><span className="button-spinner" aria-hidden="true" /> Consultando experto…</> : 'Optimizar compra'}
                      </button>
                      <span id="optimize-purchase-tooltip" role="tooltip" className="action-tooltip">
                        Compara costo, distancia, tiempo y promociones; muestra la evaluación del Sistema Experto. Usa tu ubicación o coordenadas manuales.
                      </span>
                    </div>
                    <button type="button" className="load-more-button" onClick={runCompletar} disabled={busy}>
                      Marcar como completada
                    </button>
                  </div>
                  {optimizationLoading && (
                    <div className="expert-loading-panel" role="status" aria-live="polite">
                      <span className="expert-loading-orb" aria-hidden="true">🧠</span>
                      <div><b>Generando recomendación</b><p>El Sistema Experto está evaluando precios, promociones y ubicación. Puede tardar unos segundos.</p></div>
                      <span className="expert-loading-dots" aria-hidden="true"><i /><i /><i /></span>
                    </div>
                  )}
                  {!optimizationLoading && optimizacion === null && comparacion === null && !decisionStale && detalles.length > 0 && (
                    <section className="decision-pending-card" aria-label="Decisión de compra pendiente">
                      <span aria-hidden="true">✦</span>
                      <div><b>Tu análisis de compra aparecerá aquí</b><p>Optimiza la lista para comparar precio, distancia, tiempo, promociones y evaluación experta.</p></div>
                    </section>
                  )}
                  {decisionStale && (
                    <div className="decision-difference-note" role="status">
                      <b>La lista cambió y la decisión anterior quedó desactualizada.</b>
                      <span>Vuelve a optimizar para evaluar los productos y cantidades actuales.</span>
                    </div>
                  )}
                  {comparisonLoading && <div className="live-loading" role="status"><i />Comparando precios de tu lista…</div>}
                  {locationError && (
                    <div className="location-inline-error" role="alert">
                      <span aria-hidden="true">!</span>
                      <div>
                        <b>No se pudo optimizar</b>
                        <p>{locationError}</p>
                      </div>
                    </div>
                  )}

                  <details className="list-section basket-location-panel" ref={locationPanelRef} open={locationPanelOpen} onToggle={(event) => setLocationPanelOpen(event.currentTarget.open)}>
                    <summary>
                      <span><b>Ubicación</b><small>{lat && lng ? 'Coordenadas listas para optimizar' : 'Necesaria para calcular distancia y tiempo'}</small></span>
                      <span className="disclosure-indicator" aria-hidden="true">⌄</span>
                    </summary>
                    <div className="list-section-content">
                      <p>Usamos tus coordenadas para calcular distancia y tiempo. No las guardamos en tu cuenta.</p>
                      <div className="basket-location-controls">
                      <input
                        ref={firstLocationInputRef}
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
                  </details>

                  {(promosLoading || promociones.length > 0 || promosError) && (
                    <details className="list-section promotions-section">
                      <summary><span><b>Promociones de la lista</b><small>{promosLoading ? 'Buscando ofertas…' : `${promociones.length} ofertas encontradas`}</small></span><span className="disclosure-indicator" aria-hidden="true">⌄</span></summary>
                      <div className="list-section-content">
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
                    </details>
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
                <details className="list-section comparison-section" open={comparisonOpen} onToggle={(event) => setComparisonOpen(event.currentTarget.open)}>
                  <summary><span><b>Comparación por supermercado</b><small>{comparacion.length} alternativas de precio</small></span><span className="disclosure-indicator" aria-hidden="true">⌄</span></summary>
                  <div className="list-section-content">
                  {comparacion.length === 0 && (
                    <div className="empty-optimizer"><span>🛒</span><h3>Sin precios disponibles</h3></div>
                  )}
                  {comparacion.map((r) => (
                        <article key={r.sucursalId} className="recommendation-card">
                      <div>
                        <span className="recommendation-label">{r.supermercado}</span>
                        <span className="recommendation-store">{r.sucursal}</span>
                            {r.sucursalId === [...comparacion].sort((a, b) => a.costoTotal - b.costoTotal)[0]?.sucursalId && <span className="lowest-price-tag">Precio más bajo</span>}
                        <small>
                          {r.esencialesDisponibles}/{r.esencialesTotales} esenciales
                          {r.beneficioPromociones > 0 && ` · ahorro ${formatMoney(r.beneficioPromociones)}`}
                          {r.dentroDelPresupuesto === false && ' · excede presupuesto'}
                        </small>
                      </div>
                      <b className="recommendation-total">{formatMoney(r.costoTotal)}</b>
                          <PriceProvenance resultado={r} compact />
                    </article>
                  ))}
                  </div>
                </details>
              )}

              {optimizacion !== null && optimizacion.length > 0 && (
                <section className="list-decision-panel" aria-label="Resultado de optimización">
                  {(() => {
                    const mejorScore = optimizacion[0]
                    const menorPrecio = optimizacion.reduce((best, item) => item.costoTotal < best.costoTotal ? item : best, optimizacion[0])
                    return (
                      <>
                        <div className="decision-panel-heading">
                          <span aria-hidden="true">✦</span>
                          <div><span className="eyebrow">DECISIÓN DE COMPRA</span><h2>Mejor alternativa según el optimizador</h2></div>
                        </div>
                        <article className="decision-winner-card">
                          <div className="decision-winner-top"><span>MEJOR SCORE · {mejorScore.score.toFixed(2)}</span><span className="decision-winner-price">{formatMoney(mejorScore.costoTotal)}</span></div>
                          <h3>{mejorScore.supermercado}</h3><p>{mejorScore.sucursal}</p>
                          <div className="decision-criteria">
                            <span>Score <b>{mejorScore.score.toFixed(2)}</b></span>
                            <span>Distancia <b>{mejorScore.distanciaKm != null ? `${mejorScore.distanciaKm.toFixed(1)} km` : 'No disponible'}</b></span>
                            <span>Tiempo <b>{mejorScore.tiempoMinutos != null ? `${Math.round(mejorScore.tiempoMinutos)} min` : 'No disponible'}</b></span>
                            <span>Esenciales <b>{mejorScore.esencialesDisponibles}/{mejorScore.esencialesTotales}</b></span>
                            <span>Ahorro por promociones <b>{formatMoney(mejorScore.beneficioPromociones)}</b></span>
                          </div>
                          <PriceProvenance resultado={mejorScore} />
                        </article>
                        {menorPrecio.sucursalId !== mejorScore.sucursalId && (
                          <div className="decision-difference-note" role="note">
                            <b>El precio más bajo está en {menorPrecio.supermercado}: {formatMoney(menorPrecio.costoTotal)}.</b>
                            <span>El Score considera costo, distancia, tiempo y promociones; por eso puede recomendar otra alternativa.</span>
                          </div>
                        )}

                        <section className="decision-expert-section">
                          <div className="decision-panel-heading"><span aria-hidden="true">🧠</span><div><span className="eyebrow">SISTEMA EXPERTO</span><h3>Por qué conviene esta alternativa</h3></div></div>
                          {mejorScore.expertRecommendation ? (
                            <ExpertRecommendationBadge recommendation={mejorScore.expertRecommendation} />
                          ) : (
                            <div className="expert-omission-note">
                              <b>El experto no evaluó esta alternativa.</b>
                              <span>{omissionReasonLabel(mejorScore.expertOmissionReason) ?? 'La evaluación del experto no está disponible; el ranking local sigue siendo válido.'}</span>
                            </div>
                          )}
                          {selectedId != null && (
                            <ExpertChatPanel
                              listaId={selectedId}
                              resultadoOptimizacionId={resultadoOptimizacionId}
                              alternatives={optimizacion}
                              selectedSucursalId={chatSucursalId}
                              onSelectSucursal={setChatSucursalId}
                            />
                          )}
                        </section>

                        {optimizacion.length > 1 && <details className="list-section alternatives-section">
                          <summary><span><b>Ver otras alternativas</b><small>{optimizacion.length} supermercados evaluados</small></span><span className="disclosure-indicator" aria-hidden="true">⌄</span></summary>
                          <div className="list-section-content">
                            {optimizacion.filter((item) => item.sucursalId !== mejorScore.sucursalId).map((r) => (
                              <article key={r.sucursalId} className="recommendation-card">
                                <div>
                                  <span className="recommendation-label">{r.supermercado}</span><span className="recommendation-store">{r.sucursal}</span>
                                  <small>Score {r.score.toFixed(2)} · {r.expertRecommendation ? (EXPERT_LEVEL_LABELS[r.expertRecommendation.nivelRecomendacion] ?? r.expertRecommendation.nivelRecomendacion) : `Nivel ${r.nivelOptimizacion}%`} · {formatMoney(r.costoTotal)} · {r.distanciaKm != null ? `${r.distanciaKm.toFixed(1)} km` : 'Sin distancia'} · {r.tiempoMinutos != null ? `${Math.round(r.tiempoMinutos)} min` : 'Sin tiempo'} · ahorro promociones {formatMoney(r.beneficioPromociones)}</small>
                                  <PriceProvenance resultado={r} compact />
                                  {!r.expertSystemAvailable && <div className="expert-omission-note compact"><b>Sin evaluación experta</b><span>{omissionReasonLabel(r.expertOmissionReason) ?? 'El experto no respondió para esta alternativa.'}</span></div>}
                                </div>
                                <span className="recommendation-total">{r.expertRecommendation ? (EXPERT_LEVEL_LABELS[r.expertRecommendation.nivelRecomendacion] ?? r.expertRecommendation.nivelRecomendacion) : 'Evaluación local'}</span>
                              </article>
                            ))}
                          </div>
                        </details>}
                      </>
                    )
                  })()}
                </section>
              )}
            </div>
          </div>

        </>
      )}
    </section>
  )
}
