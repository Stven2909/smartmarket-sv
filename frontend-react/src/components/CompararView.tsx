import { useCallback, useEffect, useMemo, useState } from 'react'
import { ApiError, friendlyError } from '../api/client'
import * as listsApi from '../api/lists'
import type { CompararResultado, ListaSummary, OptimizarResultado } from '../types/domain'
import { MapPin, Plus, Trophy } from 'lucide-react'

function money(value: number): string {
  return value.toLocaleString('es-SV', { style: 'currency', currency: 'USD' })
}

type Props = {
  onListasChange: (listas: ListaSummary[]) => void
  onOpenMisListas: () => void
}

export function CompararView({ onListasChange, onOpenMisListas }: Props) {
  const [listas, setListas] = useState<ListaSummary[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [comparacion, setComparacion] = useState<CompararResultado[] | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [optimizacion, setOptimizacion] = useState<OptimizarResultado[] | null>(null)
  const [lat, setLat] = useState('')
  const [lng, setLng] = useState('')
  const [geolocating, setGeolocating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const refreshListas = useCallback(async () => {
    const data = await listsApi.fetchListas()
    setListas(data)
    onListasChange(data)
    return data
  }, [onListasChange])

  useEffect(() => {
    refreshListas().catch(() => setError('No se pudieron cargar tus listas.'))
  }, [refreshListas])

  useEffect(() => {
    if (listas.length > 0 && selectedId == null) {
      setSelectedId(listas[0].id)
      return
    }
    if (selectedId == null) return
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    setOptimizacion(null)
    listsApi
      .compararLista(selectedId)
      .then((data) => {
        if (!controller.signal.aborted) setComparacion(data.resultados)
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(friendlyError(e, 'No se pudo comparar la lista.'))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, listas])

  const sorted = useMemo(
    () => (comparacion ? [...comparacion].sort((a, b) => a.costoTotal - b.costoTotal) : []),
    [comparacion],
  )
  const podium = sorted.slice(0, 3)
  const best = podium[0]

  async function runOptimizar() {
    const latValue = Number(lat)
    const lngValue = Number(lng)
    if (!latValue || !lngValue) {
      setError('Necesitas latitud y longitud para optimizar la ruta.')
      return
    }
    if (!selectedId) return
    setError(null)
    try {
      const data = await listsApi.optimizarLista(selectedId, latValue, lngValue)
      setOptimizacion(data.resultados)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo optimizar la ruta.')
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

  function selectLista(id: number) {
    setSelectedId(id)
    setDetailOpen(false)
  }

  return (
    <div className="view" style={{ maxWidth: 860 }}>
      <div className="page-heading">
        <div className="eyebrow"><span />COMPARAR</div>
        <h1>¿Dónde te conviene comprar hoy?</h1>
      </div>

      {error && <div className="live-error"><b>Aviso</b><span>{error}</span></div>}

      {listas.length === 0 ? (
        <div className="empty-state">
          <h3>Todavía no tienes listas</h3>
          <p>Crea una lista, agrega tus productos y volvé para ver cuál supermercado tiene el mejor precio.</p>
          <button type="button" className="add-button" onClick={onOpenMisListas}>
            <Plus size={16} /> Crear mi primera lista
          </button>
        </div>
      ) : (
        <>
          <div className="category-filters" style={{ marginBottom: 18 }}>
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

          {loading && <div className="live-loading"><i />Comparando precios…</div>}

          {!loading && comparacion !== null && comparacion.length === 0 && (
            <div className="empty-state compact">
              <h3>Sin precios disponibles</h3>
              <p>Esta lista aún no tiene productos con precios publicados.</p>
            </div>
          )}

          {comparacion !== null && comparacion.length > 0 && (
            <section className="optimizer-panel">
              <div className="optimizer-head">
                <span className="spark-icon"><Trophy size={20} /></span>
                <div>
                  <span>MEJOR OPCIÓN</span>
                  <h2>Podio de precios</h2>
                </div>
              </div>

              <div className="podium-list">
                {podium.map((r, index) => (
                  <article key={r.sucursalId} className={`podium-item${index === 0 ? ' first' : ''}`}>
                    <span className="podium-medal">{index + 1}</span>
                    <div className="podium-store">
                      <b>{r.supermercado}</b>
                      <small>{r.sucursal} · {r.esencialesDisponibles}/{r.esencialesTotales} esenciales</small>
                    </div>
                    <div className="podium-cost">
                      <b>{money(r.costoTotal)}</b>
                      {index === 0
                        ? <small className="podium-save">Mejor precio</small>
                        : best
                          ? <small>+{money(r.costoTotal - best.costoTotal)} vs mejor</small>
                          : <small>{r.dentroDelPresupuesto === false ? 'Excede presupuesto' : ''}</small>}
                    </div>
                  </article>
                ))}
              </div>

              <div className="category-filters" style={{ marginTop: 16 }}>
                <button type="button" className="add-button" onClick={() => setDetailOpen((v) => !v)}>
                  {detailOpen ? 'Ocultar detalle' : 'Ver detalle'}
                </button>
                <button type="button" className="load-more-button" onClick={runOptimizar}>
                  Optimizar ruta
                </button>
              </div>

              {detailOpen && (
                <div className="store-table">
                  <div className="store-table-head">
                    <span>Supermercado</span>
                    <span>Esenciales</span>
                    <span>Costo</span>
                  </div>
                  {sorted.map((r) => (
                    <div key={r.sucursalId} className="store-table-row">
                      <div>
                        <b>{r.supermercado}</b>
                        <small> · {r.sucursal}</small>
                      </div>
                      <span>{r.esencialesDisponibles}/{r.esencialesTotales}</span>
                      <span className="saving-price" style={{ justifyContent: 'center' }}>
                        <b>{money(r.costoTotal)}</b>
                        <small>{r.beneficioPromociones > 0 ? `ahorro ${money(r.beneficioPromociones)}` : ''}</small>
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {optimizacion !== null && optimizacion.length > 0 && (
                <div className="optimizer-panel" style={{ marginTop: 18 }}>
                  <div className="optimizer-head">
                    <span className="spark-icon"><MapPin size={20} /></span>
                    <div>
                      <span>MEJOR RUTA (SCORE)</span>
                      <h2>Menor score = mejor compra</h2>
                    </div>
                  </div>
                  {optimizacion.map((r) => (
                    <article
                      key={r.sucursalId}
                      className={`recommendation-card${optimizacion[0].sucursalId === r.sucursalId ? ' best' : ''}`}
                    >
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

              <div className="basket-location-panel" style={{ marginTop: 18 }}>
                <span>UBICACIÓN OPCIONAL</span>
                <p>Para optimizar la ruta necesitamos tu latitud y longitud. No guardamos coordenadas.</p>
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
            </section>
          )}
        </>
      )}
    </div>
  )
}
