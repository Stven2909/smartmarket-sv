import { useCallback, useEffect, useMemo, useState } from 'react'
import { ApiError, friendlyError } from '../api/client'
import * as listsApi from '../api/lists'
import { supermarketColor } from '../lib/presentation'
import type { CompararResultado, ListaSummary, OptimizarResultado } from '../types/domain'
import { Check, MapPin, Navigation, Plus, Trophy } from 'lucide-react'

function money(value: number): string {
  return value.toLocaleString('es-SV', { style: 'currency', currency: 'USD' })
}

// Reverse geocoding con Nominatim/OSM (gratis, sin key). No es un dato del motor:
// solo le da nombre humano a la ubicación del usuario. Si falla, se muestra
// "Tu ubicación actual" — nunca se inventa ni se muestran coordenadas crudas.
async function reverseGeocode(lat: number, lng: number): Promise<string | null> {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&accept-language=es`,
      { headers: { Accept: 'application/json' } },
    )
    if (!res.ok) return null
    const data = await res.json()
    const a = data.address ?? {}
    const city = a.city ?? a.town ?? a.municipality ?? a.county ?? a.state
    if (!city) return null
    return a.state && a.state !== city ? `${city}, ${a.state}` : city
  } catch {
    return null
  }
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
  const [ubicacionLabel, setUbicacionLabel] = useState<string | null>(null)
  const [geolocating, setGeolocating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const refreshListas = useCallback(async () => {
    const data = await listsApi.fetchListas('activa')
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

  // Podio: ordenado por costo; el ganador es la opción más barata.
  const sorted = useMemo(
    () => (comparacion ? [...comparacion].sort((a, b) => a.costoTotal - b.costoTotal) : []),
    [comparacion],
  )
  const winner = sorted[0]
  const runnerUp = sorted[1]
  const ahorroVsSiguiente = winner && runnerUp ? runnerUp.costoTotal - winner.costoTotal : 0
  const podium = useMemo(
    () => [runnerUp, winner, sorted[2]].filter((r): r is CompararResultado => Boolean(r)),
    [runnerUp, winner, sorted],
  )

  // Ruta: ordenada por Score (menor = mejor, fórmula congelada §5.1).
  const rutaOrdenada = useMemo(
    () => (optimizacion ? [...optimizacion].sort((a, b) => a.score - b.score) : []),
    [optimizacion],
  )
  const rutaMejor = rutaOrdenada[0]

  // "Nivel de optimización" del ganador: real, del motor, solo tras optimizar.
  const nivelGanador = useMemo(() => {
    if (!winner || !optimizacion) return null
    const r = optimizacion.find((x) => x.sucursalId === winner.sucursalId)
    return r ? r.nivelOptimizacion : null
  }, [winner, optimizacion])

  async function runOptimizar(lat: number, lng: number) {
    if (!selectedId) return
    setError(null)
    try {
      const data = await listsApi.optimizarLista(selectedId, lat, lng)
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
    setError(null)
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude
        const lng = pos.coords.longitude
        setUbicacionLabel((await reverseGeocode(lat, lng)) ?? 'Tu ubicación actual')
        await runOptimizar(lat, lng)
        setGeolocating(false)
      },
      () => {
        setGeolocating(false)
        setError('No pudimos obtener tu ubicación. Aceptá el permiso e intentá de nuevo.')
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 30000 },
    )
  }

  function selectLista(id: number) {
    setSelectedId(id)
    setDetailOpen(false)
    setUbicacionLabel(null)
  }

  return (
    <div className="view compare-view" style={{ maxWidth: 860 }}>
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

          {winner && !loading && (
            <div className="compare-narrative" key={selectedId}>
              <div className="compare-stats">
                {runnerUp && (
                  <span className="stat-chip"><span>💰</span><span>Ahorras <b>{money(ahorroVsSiguiente)}</b></span></span>
                )}
                <span className="stat-chip"><span>🛒</span><span>{winner.todosLosEsenciales ? <b>Lista completa</b> : `${winner.esencialesDisponibles}/${winner.esencialesTotales} esenciales`}</span></span>
                {rutaMejor && (
                  <span className="stat-chip"><span>📍</span><span>Ruta <b>{Math.round(rutaMejor.tiempoMinutos)} min</b></span></span>
                )}
              </div>

              <section className="podium-panel">
                <div className="podium-heading">
                  <span className="spark-icon"><Trophy size={20} /></span>
                  <div>
                    <span className="eyebrow">RECOMENDACIÓN</span>
                    <h2>Tu compra ya tiene un ganador.</h2>
                    <p>Comparado con los precios y promociones de hoy.</p>
                  </div>
                </div>

                <div className="podium-stage">
                  {podium.map((r, i) => {
                    const isWinner = r.sucursalId === winner.sucursalId
                    return (
                      <article
                        key={r.sucursalId}
                        className={`podium-place${isWinner ? ' winner' : ''}`}
                        style={{ animationDelay: `${i * 90}ms` }}
                      >
                        <span className="podium-medal">{isWinner ? '🥇' : i === 1 ? '🥈' : '🥉'}</span>
                        <span className="store-badge" style={{ background: supermarketColor(r.supermercado) }}>
                          {r.supermercado.slice(0, 2).toUpperCase()}
                        </span>
                        <b className="podium-store">{r.supermercado}</b>
                        <small className="podium-branch">{r.sucursal}</small>
                        {isWinner ? (
                          <>
                            <span className="podium-price winner-price">{money(r.costoTotal)}</span>
                            <span className="podium-label">Tu mejor opción hoy</span>
                          </>
                        ) : (
                          <>
                            <span className="podium-price">{money(r.costoTotal)}</span>
                            <span className="podium-vs">{runnerUp && winner ? `+${money(r.costoTotal - winner.costoTotal)} vs mejor` : ''}</span>
                          </>
                        )}
                      </article>
                    )
                  })}
                </div>

                <div className="winner-foot">
                  <span className="winner-seal"><Check size={14} /> Recomendado por SmartMarket</span>
                  {nivelGanador != null && (
                    <div className="confidence">
                      <div className="confidence-label">
                        <span>Nivel de optimización</span>
                        <b>{Math.round(nivelGanador)}%</b>
                      </div>
                      <div className="confidence-bar"><i style={{ width: `${nivelGanador}%` }} /></div>
                    </div>
                  )}
                </div>
              </section>

              <section className="why-panel">
                <div className="why-head">
                  <span className="eyebrow">LA DECISIÓN</span>
                  <h3>¿Por qué ganó {winner.supermercado}?</h3>
                </div>
                <ul className="why-list">
                  {runnerUp && ahorroVsSiguiente > 0 && (
                    <li><Check size={15} /><span><b>Ahorras {money(ahorroVsSiguiente)}</b> vs la segunda opción</span></li>
                  )}
                  <li>
                    <Check size={15} />
                    <span>
                      {winner.todosLosEsenciales
                        ? <b>Lista completa</b>
                        : <b>{winner.esencialesDisponibles} de {winner.esencialesTotales}</b>}
                      {winner.todosLosEsenciales ? ' · todos tus esenciales disponibles' : ' esenciales disponibles'}
                    </span>
                  </li>
                  {winner.productosConPromocion > 0 && (
                    <li>
                      <Check size={15} />
                      <span><b>{winner.productosConPromocion} producto{winner.productosConPromocion === 1 ? '' : 's'} en promoción</b> · ahorro {money(winner.beneficioPromociones)}</span>
                    </li>
                  )}
                  {winner.dentroDelPresupuesto != null && (
                    <li className={winner.dentroDelPresupuesto ? '' : 'warn'}>
                      <Check size={15} />
                      <span>{winner.dentroDelPresupuesto ? <b>Dentro del presupuesto</b> : <b>Excede el presupuesto</b>}</span>
                    </li>
                  )}
                </ul>
              </section>

              <div className="category-filters" style={{ marginTop: 18, justifyContent: 'center' }}>
                <button type="button" className="load-more-button" onClick={() => setDetailOpen((v) => !v)}>
                  {detailOpen ? 'Ocultar detalle' : 'Ver detalle'}
                </button>
              </div>

              {detailOpen && (
                <section className="store-table" style={{ marginTop: 14 }}>
                  <div className="store-table-head">
                    <span>Supermercado</span>
                    <span>Esenciales</span>
                    <span>Costo</span>
                  </div>
                  {sorted.map((r) => (
                    <div key={r.sucursalId} className="store-table-row">
                      <div className="store-table-store">
                        <span className="store-badge" style={{ background: supermarketColor(r.supermercado) }}>
                          {r.supermercado.slice(0, 2).toUpperCase()}
                        </span>
                        <div>
                          <b>{r.supermercado}</b>
                          <small> · {r.sucursal}</small>
                        </div>
                      </div>
                      <span>{r.esencialesDisponibles}/{r.esencialesTotales}</span>
                      <span className="saving-price" style={{ justifyContent: 'flex-end' }}>
                        <b>{money(r.costoTotal)}</b>
                        {r.beneficioPromociones > 0 && <small className="saving">ahorro {money(r.beneficioPromociones)}</small>}
                      </span>
                    </div>
                  ))}
                </section>
              )}

              <section className="location-panel" style={{ marginTop: 18 }}>
                <div className="location-head">
                  <span className="location-icon"><MapPin size={18} /></span>
                  <div>
                    <span className="eyebrow">UBICACIÓN</span>
                    <p>Optimizamos la ruta según dónde estés. No guardamos coordenadas.</p>
                  </div>
                </div>
                {ubicacionLabel ? (
                  <div className="location-done">
                    <span className="location-chip">📍 {ubicacionLabel}</span>
                    <button type="button" className="link-button" onClick={useGeolocation} disabled={geolocating}>
                      {geolocating ? 'Calculando…' : 'Cambiar ubicación'}
                    </button>
                  </div>
                ) : (
                  <button type="button" className="add-button" onClick={useGeolocation} disabled={geolocating}>
                    <MapPin size={16} /> {geolocating ? 'Obteniendo ubicación…' : 'Optimizar según mi ubicación'}
                  </button>
                )}
              </section>

              {rutaMejor && (
                <section className="route-panel" style={{ marginTop: 18 }}>
                  <div className="route-head">
                    <span className="route-icon"><Navigation size={18} /></span>
                    <div>
                      <span className="eyebrow">RUTA</span>
                      <h3>Ruta recomendada</h3>
                    </div>
                  </div>
                  <div className="route-hero">
                    <div className="route-primary">
                      <span className="route-time">{Math.round(rutaMejor.tiempoMinutos)} min</span>
                      <span className="route-km">{rutaMejor.distanciaKm.toFixed(1)} km</span>
                    </div>
                    <div className="route-meta">
                      <span>Gas estimado <b>{money(rutaMejor.costoCombustible)}</b></span>
                      <span>{rutaMejor.supermercado} · {rutaMejor.sucursal}</span>
                    </div>
                  </div>
                  {rutaOrdenada.length > 1 && (
                    <div className="route-list">
                      {rutaOrdenada.slice(1).map((r) => (
                        <div key={r.sucursalId} className="route-item">
                          <span className="store-badge" style={{ background: supermarketColor(r.supermercado) }}>
                            {r.supermercado.slice(0, 2).toUpperCase()}
                          </span>
                          <div>
                            <b>{r.supermercado}</b>
                            <small> · {r.sucursal}</small>
                          </div>
                          <span>{Math.round(r.tiempoMinutos)} min · {r.distanciaKm.toFixed(1)} km</span>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
