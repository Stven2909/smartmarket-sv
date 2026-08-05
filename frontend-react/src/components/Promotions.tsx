import { useEffect, useState } from 'react'
import { fetchPromociones } from '../api/promos'
import { friendlyError } from '../api/client'
import type { Promotion } from '../types/domain'

function money(value: number): string {
  return value.toLocaleString('es-SV', { style: 'currency', currency: 'USD' })
}

export function Promotions() {
  const [promotions, setPromotions] = useState<Promotion[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    fetchPromociones(undefined, controller.signal)
      .then(setPromotions)
      .catch((e) => setError(friendlyError(e, 'No pudimos cargar las promociones en este momento.')))
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [])

  const visible = promotions.slice(0, 8)

  return (
    <section className="promotions-view">
      <div className="section-title-row">
        <div>
          <div className="eyebrow"><span />MEJORES PROMOCIONES</div>
          <h2>Promociones activas</h2>
        </div>
      </div>

      {loading && <div className="live-loading">Cargando promociones…</div>}
      {error && (
        <div className="live-error"><b>Promociones no disponibles</b><span>{error}</span></div>
      )}

      {!loading && !error && visible.length === 0 && (
        <div className="empty-state compact">
          <span>🏷️</span>
          <h3>Sin promociones activas</h3>
          <p>Cuando los supermercados publiquen ofertas, aparecerán aquí.</p>
        </div>
      )}

      {!loading && !error && visible.length > 0 && (
        <div className="promotions-grid">
          {visible.map((promo) => (
            <article key={promo.id} className="promotion-card">
              <div className="promotion-visual">
                <span className="promotion-emoji">{promo.categoryIcon}</span>
                {promo.discountPercent != null && (
                  <span className="promotion-badge">-{promo.discountPercent}%</span>
                )}
              </div>
              <div className="promotion-body">
                <span className="promotion-time">{promo.supermarketName}</span>
                <h3>{promo.productName}</h3>
                <p>{[promo.unitLabel, promo.categoryName].filter(Boolean).join(' · ')}</p>
                <div className="promotion-price">
                  {promo.previousPrice != null && <s>{money(promo.previousPrice)}</s>}
                  <b>{money(promo.price)}</b>
                  {promo.savings != null && (
                    <span className="live-saving">Ahorras {money(promo.savings)}</span>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
