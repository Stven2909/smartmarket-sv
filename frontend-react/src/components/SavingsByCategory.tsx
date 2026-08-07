import { useEffect, useState } from 'react'
import { fetchPromociones } from '../api/promos'
import { friendlyError } from '../api/client'
import { formatMoney } from '../lib/format'
import type { Promotion } from '../types/domain'

// Agrupa las promociones por categoría y destaca el mejor ahorro de cada una.
export function SavingsByCategory() {
  const [promotions, setPromotions] = useState<Promotion[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    fetchPromociones(undefined, controller.signal)
      .then(setPromotions)
      .catch((e) => setError(friendlyError(e, 'No pudimos cargar los ahorros en este momento.')))
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [])

  const groups = new Map<string, Promotion[]>()
  for (const promo of promotions) {
    const key = promo.categoryName || 'Otros'
    const list = groups.get(key) ?? []
    list.push(promo)
    groups.set(key, list)
  }

  return (
    <section className="category-savings-group">
      <div className="section-title-row">
        <div>
          <div className="eyebrow"><span />AHORRO POR CATEGORÍA</div>
          <h2>Mejores ahorros en cada categoría</h2>
        </div>
      </div>

      {loading && <div className="live-loading">Cargando ahorros…</div>}
      {error && (
        <div className="live-error"><b>Ahorros no disponibles</b><span>{error}</span></div>
      )}

      {!loading && !error && groups.size === 0 && (
        <div className="empty-state compact">
          <span>📊</span>
          <h3>Sin ahorros que mostrar</h3>
          <p>Las promociones activas aparecerán agrupadas por categoría.</p>
        </div>
      )}

      {!loading && !error && groups.size > 0 && (
        <div className="category-savings-list">
          {[...groups.entries()].map(([category, items]) => {
            const best = [...items].sort((a, b) => (b.discountPercent ?? 0) - (a.discountPercent ?? 0))[0]
            return (
              <article key={category} className="saving-card">
                <div className="saving-percent">
                  {best?.discountPercent != null ? `-${best.discountPercent}%` : '🏷️'}
                </div>
                <div className="saving-price">
                  <h3>{category}</h3>
                  <p>{best ? `${best.productName} en ${best.supermarketName}` : 'Sin ofertas activas'}</p>
                  {best && (
                    <div>
                      <s>{best.previousPrice != null ? formatMoney(best.previousPrice) : ''}</s>
                      <b>{formatMoney(best.price)}</b>
                    </div>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
