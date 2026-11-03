import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ApiError, friendlyError } from '../api/client'
import * as listsApi from '../api/lists'
import { formatMoney } from '../lib/format'
import { supermarketColor } from '../lib/presentation'
import type { CompararResultado, ListaSummary, OptimizarResultado } from '../types/domain'
import { Check, MapPin, Navigation, Plus, Trophy } from 'lucide-react'
import { ExpertChatPanel } from './ExpertChatPanel'
import { ExpertRecommendationBadge } from './ExpertRecommendationBadge'
import { LocationConsentDialog } from './LocationConsentDialog'
import { ExpertEvaluationToast } from './ExpertEvaluationToast'
import { PriceProvenance } from './PriceProvenance'
import { omissionReasonLabel } from '../lib/expertLabels'

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
  const selectedIdRef = useRef<number | null>(null)
  selectedIdRef.current = selectedId
  const [comparacion, setComparacion] = useState<CompararResultado[] | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [optimizacion, setOptimizacion] = useState<OptimizarResultado[] | null>(null)
  const [resultadoOptimizacionId, setResultadoOptimizacionId] = useState<number | null>(null)
  const [chatSucursalId, setChatSucursalId] = useState<number | null>(null)
  const [ubicacionLabel, setUbicacionLabel] = useState<string | null>(null)
  const [geolocating, setGeolocating] = useState(false)
  const [locationConsentOpen, setLocationConsentOpen] = useState(false)
  const [locationNotice, setLocationNotice] = useState<string | null>(null)
  const locationNoticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [expertEvaluatedNotice, setExpertEvaluatedNotice] = useState(false)
  const expertNoticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const geolocationRequestId = useRef(0)
  const optimizationRequestId = useRef(0)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => () => {
    if (locationNoticeTimer.current) clearTimeout(locationNoticeTimer.current)
    if (expertNoticeTimer.current) clearTimeout(expertNoticeTimer.current)
  }, [])

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
    setResultadoOptimizacionId(null)
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
  const precioMasBajo = winner
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

  async function runOptimizar(lat: number, lng: number): Promise<boolean> {
    if (!selectedId) return false
    const listId = selectedId
    const requestId = ++optimizationRequestId.current
    setError(null)
    setExpertEvaluatedNotice(false)
    setChatSucursalId(null)
    try {
      const data = await listsApi.optimizarLista(listId, lat, lng)
      if (requestId !== optimizationRequestId.current) return false
      setOptimizacion(data.resultados)
      setResultadoOptimizacionId(data.resultadoOptimizacionId)
      const mejorEvaluada = data.resultados
        .filter((resultado) => resultado.expertSystemAvailable && resultado.expertRecommendation)
        .sort((a, b) => a.score - b.score)[0]
      setChatSucursalId(mejorEvaluada?.sucursalId ?? null)
      if (data.resultados.some((resultado) => resultado.expertSystemAvailable && resultado.expertRecommendation)) {
        setExpertEvaluatedNotice(true)
        if (expertNoticeTimer.current) clearTimeout(expertNoticeTimer.current)
        expertNoticeTimer.current = setTimeout(() => setExpertEvaluatedNotice(false), 5200)
      }
      return true
    } catch (e) {
      if (requestId === optimizationRequestId.current) setError(e instanceof ApiError ? e.message : 'No se pudo optimizar la ruta.')
      return false
    }
  }

  function useGeolocation() {
    setLocationConsentOpen(true)
  }

  function confirmUseGeolocation() {
    setLocationConsentOpen(false)
    const listIdAtRequest = selectedIdRef.current
    const requestId = ++geolocationRequestId.current
    if (!('geolocation' in navigator)) {
      setError('Tu navegador no soporta geolocalización.')
      return
    }
    setGeolocating(true)
    setError(null)
    setLocationNotice(null)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        if (requestId !== geolocationRequestId.current || selectedIdRef.current !== listIdAtRequest) {
          setGeolocating(false)
          return
        }
        const lat = pos.coords.latitude
        const lng = pos.coords.longitude
        void reverseGeocode(lat, lng).then((label) => {
          if (requestId === geolocationRequestId.current && selectedIdRef.current === listIdAtRequest) {
            setUbicacionLabel(label ?? 'Tu ubicación actual')
          }
        })

        void runOptimizar(lat, lng).then((success) => {
          if (requestId !== geolocationRequestId.current || selectedIdRef.current !== listIdAtRequest) return
          setGeolocating(false)
          if (!success) return
          setLocationNotice('Ahora el sistema está usando tu ubicación para calcular la mejor alternativa.')
          if (locationNoticeTimer.current) clearTimeout(locationNoticeTimer.current)
          locationNoticeTimer.current = setTimeout(() => setLocationNotice(null), 4500)
        })
      },
      () => {
        if (requestId !== geolocationRequestId.current || selectedIdRef.current !== listIdAtRequest) return
        setGeolocating(false)
        setError('No pudimos obtener tu ubicación. Aceptá el permiso e intentá de nuevo.')
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 30000 },
    )
  }

  function selectLista(id: number) {
    geolocationRequestId.current += 1
    optimizationRequestId.current += 1
    selectedIdRef.current = id
    setSelectedId(id)
    setGeolocating(false)
    setDetailOpen(false)
    setUbicacionLabel(null)
    setLocationNotice(null)
    setExpertEvaluatedNotice(false)
    setChatSucursalId(null)
  }

  return (
    <div className="view compare-view" style={{ maxWidth: 860 }}>
      <ExpertEvaluationToast visible={expertEvaluatedNotice} />
      <div className="page-heading">
        <div className="eyebrow"><span />COMPARAR</div>
        <h1>¿Dónde te conviene comprar hoy?</h1>
      </div>

      {error && <div className="live-error"><b>Aviso</b><span>{error}</span></div>}

      {locationConsentOpen && (
        <LocationConsentDialog
          description="SmartMarket usará tus coordenadas para calcular distancias y tiempos. También las enviará a OpenStreetMap para mostrar el nombre de la zona. No guardamos las coordenadas en tu cuenta. Tu navegador te pedirá permiso."
          onCancel={() => setLocationConsentOpen(false)}
          onConfirm={confirmUseGeolocation}
        />
      )}

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
                <span className="stat-chip"><span>🏷️</span><span>Precio más bajo <b>{precioMasBajo.supermercado}</b></span></span>
                {rutaMejor && <span className="stat-chip"><span>⚖️</span><span>Mejor Score <b>{rutaMejor.supermercado}</b></span></span>}
                {runnerUp && (
                  <span className="stat-chip"><span>💰</span><span>Ahorras <b>{formatMoney(ahorroVsSiguiente)}</b></span></span>
                )}
                <span className="stat-chip"><span>🛒</span><span>{winner.todosLosEsenciales ? <b>Lista completa</b> : `${winner.esencialesDisponibles}/${winner.esencialesTotales} esenciales`}</span></span>
                {rutaMejor && rutaMejor.tiempoMinutos != null && (
                  <span className="stat-chip"><span>📍</span><span>Ruta <b>{Math.round(rutaMejor.tiempoMinutos)} min</b></span></span>
                )}
              </div>

              {rutaMejor && precioMasBajo.sucursalId !== rutaMejor.sucursalId && (
                <div className="decision-difference-note" role="note">
                  <b>El precio más bajo y el mejor Score corresponden a supermercados distintos.</b>
                  <span>El precio más bajo está en {precioMasBajo.supermercado} ({formatMoney(precioMasBajo.costoTotal)}); el Score combina costo, distancia, tiempo y promociones y favorece a {rutaMejor.supermercado}.</span>
                </div>
              )}

              {rutaMejor && (
                <section className="expert-decision-panel" aria-label="Recomendación del Sistema Experto">
                  <div className="expert-decision-heading">
                    <span aria-hidden="true">🧠</span>
                    <div>
                      <span className="eyebrow">ANÁLISIS DEL SISTEMA EXPERTO</span>
                      <h2>La mejor alternativa según el Score</h2>
                      <p>{rutaMejor.supermercado} · {rutaMejor.sucursal}</p>
                      <p className="compare-score-line">Score {rutaMejor.score.toFixed(2)} · Nivel de optimización {rutaMejor.nivelOptimizacion}%</p>
                    </div>
                  </div>
                  <p className="expert-decision-context">El optimizador ordena las opciones por costo, distancia y tiempo. El experto explica la conveniencia de cada alternativa con sus reglas.</p>
                  {rutaMejor.expertRecommendation ? (
                    <>
                      <ExpertRecommendationBadge recommendation={rutaMejor.expertRecommendation} />
                      {rutaMejor.expertRecommendation.chatbotAvailable === false && (
                        <p className="expert-unavailable-note">El asistente explicativo no está disponible temporalmente; los datos de precio y ruta siguen disponibles.</p>
                      )}
                    </>
                  ) : (
                    <div className="expert-unavailable-note">
                      {rutaMejor.expertOmissionReason
                        ? `El experto omitió esta alternativa: ${omissionReasonLabel(rutaMejor.expertOmissionReason)}`
                        : 'El Sistema Experto no está disponible. La alternativa se ordenó con los datos de costo, distancia y promociones.'}
                    </div>
                  )}
                  <ExpertChatPanel
                    listaId={selectedId!}
                    resultadoOptimizacionId={resultadoOptimizacionId}
                    alternatives={rutaOrdenada}
                    selectedSucursalId={chatSucursalId}
                    onSelectSucursal={setChatSucursalId}
                  />
                  <PriceProvenance resultado={rutaMejor} />
                </section>
              )}

              <section className="podium-panel">
                <div className="podium-heading">
                  <span className="spark-icon"><Trophy size={20} /></span>
                  <div>
                    <span className="eyebrow">PRECIO MÁS BAJO</span>
                    <h2>Esta alternativa tiene el menor costo.</h2>
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
                        <span className="podium-medal">{isWinner ? '🥇' : r.sucursalId === runnerUp?.sucursalId ? '🥈' : '🥉'}</span>
                        <span className="store-badge" style={{ background: supermarketColor(r.supermercado) }}>
                          {r.supermercado.slice(0, 2).toUpperCase()}
                        </span>
                        <b className="podium-store">{r.supermercado}</b>
                        <small className="podium-branch">{r.sucursal}</small>
                        {isWinner ? (
                          <>
                            <span className="podium-price winner-price">{formatMoney(r.costoTotal)}</span>
                            <span className="podium-label">Precio más bajo</span>
                          </>
                        ) : (
                          <>
                            <span className="podium-price">{formatMoney(r.costoTotal)}</span>
                            <span className="podium-vs">{runnerUp && winner ? `+${formatMoney(r.costoTotal - winner.costoTotal)} vs mejor` : ''}</span>
                          </>
                        )}
                        <PriceProvenance resultado={r} compact />
                      </article>
                    )
                  })}
                </div>

                <div className="winner-foot">
                  <span className="winner-seal"><Check size={14} /> Menor precio de la lista</span>
                </div>
              </section>

              <section className="why-panel">
                <div className="why-head">
                  <span className="eyebrow">LA DECISIÓN</span>
                  <h3>Detalle del precio más bajo</h3>
                </div>
                <ul className="why-list">
                  {runnerUp && ahorroVsSiguiente > 0 && (
                    <li><Check size={15} /><span><b>Ahorras {formatMoney(ahorroVsSiguiente)}</b> vs la segunda opción</span></li>
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
                      <span><b>{winner.productosConPromocion} producto{winner.productosConPromocion === 1 ? '' : 's'} en promoción</b> · ahorro {formatMoney(winner.beneficioPromociones)}</span>
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
                      <div className="saving-price" style={{ justifyContent: 'flex-end' }}>
                        <b>{formatMoney(r.costoTotal)}</b>
                        {r.beneficioPromociones > 0 && <small className="saving">ahorro {formatMoney(r.beneficioPromociones)}</small>}
                        <PriceProvenance resultado={r} compact />
                      </div>
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
                {locationNotice && <div className="location-status-toast" role="status">📍 {locationNotice}</div>}
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
                      <span className="route-time">{rutaMejor.tiempoMinutos != null ? `${Math.round(rutaMejor.tiempoMinutos)} min` : '—'}</span>
                    </div>
                    <div className="route-meta">
                      <span>Distancia <b>≈ {rutaMejor.distanciaKm != null ? `${rutaMejor.distanciaKm.toFixed(1)} km` : '—'}</b></span>
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
                          <span>{r.tiempoMinutos != null ? `${Math.round(r.tiempoMinutos)} min` : '—'} · {r.distanciaKm != null ? `${r.distanciaKm.toFixed(1)} km` : '—'}</span>
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
