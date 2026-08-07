import { Check } from 'lucide-react'
import { formatMoney } from '../lib/format'
import type { Product } from '../types/domain'

type Props = {
  product: Product
  onAddToList?: (product: Product) => void
}

export function ProductCard({ product, onAddToList }: Props) {
  const offers = [...product.offers].sort((a, b) => a.price - b.price)
  const best = offers[0]

  return (
    <article className="live-product-card">
      <div className="live-product-title">
        <span className="product-emoji">{product.categoryIcon}</span>
        <div>
          <h3>{product.name}</h3>
          <p>{[product.unitLabel, product.categoryName].filter(Boolean).join(' · ')}</p>
        </div>
        {offers.length > 0 && <em>{offers.length} {offers.length === 1 ? 'precio' : 'precios'}</em>}
      </div>

      {offers.length === 0 && (
        <div className="empty-state compact">
          <span>🛒</span>
          <h3>Sin precios publicados</h3>
          <p>Este producto no tiene precios cargados todavía.</p>
        </div>
      )}

      {offers.length > 0 && best && (
        <div className="live-offers">
          {offers.map((offer, idx) => {
            const isCheapest = offers.length > 1 && idx === 0
            return (
              <div key={offer.branchId} className={`best-offer-line${isCheapest ? ' cheapest' : ''}`}>
                <div>
                  <strong>{offer.supermarketName}</strong>
                  <span>{offer.branchName}</span>
                  {isCheapest && (
                    <span className="cheapest-badge"><Check size={11} /> Más barato</span>
                  )}
                  {offer.hasPromo && offer.previousPrice != null && (
                    <span className="promotion-badge">
                      -{offer.discountPercent}%
                    </span>
                  )}
                </div>
                <div className="saving-price">
                  {offer.hasPromo && offer.previousPrice != null && (
                    <s>{formatMoney(offer.previousPrice)}</s>
                  )}
                  <b>{formatMoney(offer.price)}</b>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {onAddToList && (
        <button type="button" className="live-add-button" onClick={() => onAddToList(product)}>
          + Agregar a mi lista
        </button>
      )}
    </article>
  )
}
